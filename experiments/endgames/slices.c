/*
 * Tablebase slices for endgame.py: White's pawns stand on fixed squares; every placement of the
 * other pieces, both sides to move, gets its Syzygy WDL and a "quiet" flag. Built into
 * data/endgames/slices.so by the Makefile.
 */
#include "tbprobe.c"

int slices_init(const char *path) { return tb_init(path) ? (int)TB_LARGEST : -1; }

static uint64_t attackers(const Pos *p, unsigned sq, int white) {
    uint64_t occupied = p->white | p->black;
    uint64_t a = (king_attacks(sq) & p->kings) | (knight_attacks(sq) & p->knights)
               | (rook_attacks(sq, occupied) & (p->rooks | p->queens))
               | (bishop_attacks(sq, occupied) & (p->bishops | p->queens))
               | (pawn_attacks(sq, !white) & p->pawns);
    return a & (white ? p->white : p->black);
}

/* Quiet: the side to move is not in check, has no capture after which the capturing piece is
 * safe, and no queen, rook, bishop or knight of either side is attacked and undefended. */
static int quiet(const Pos *p) {
    if (is_check(p)) return 0;
    for (uint64_t b = (p->white | p->black) & ~p->kings & ~p->pawns; b; b &= b - 1) {
        unsigned sq = lsb(b);
        int white = (p->white >> sq) & 1;
        if (attackers(p, sq, !white) && !attackers(p, sq, white)) return 0;
    }
    TbMove moves[TB_MAX_MOVES];
    TbMove *end = gen_legal(p, moves);
    for (TbMove *m = moves; m < end; m++) {
        if (!is_capture(p, *m)) continue;
        Pos next;
        do_move(&next, p, *m);
        if (!attackers(&next, move_to(*m), next.turn)) return 0;
    }
    return 1;
}

/*
 * pieces[i] = colour * 8 + type (type 1 P .. 6 K, colour 0 White) of the n free pieces; pawns =
 * White's pawns. Index, most significant first: side to move (0 White), then the square of each
 * free piece. wdl: 0..4 = WDL + 2 from the side to move, 5 = two pieces on one square,
 * 6 = illegal, 7 = probe failed. Returns the number of failed probes.
 */
long slices_probe(int n, const int *pieces, uint64_t pawns, int8_t *wdl, uint8_t *is_quiet) {
    long total = 2;
    for (int i = 0; i < n; i++) total *= 64;
    long failures = 0;
    #pragma omp parallel for schedule(dynamic, 4096) reduction(+:failures)
    for (long idx = 0; idx < total; idx++) {
        uint64_t colour[2] = {pawns, 0}, type[7] = {0, pawns}, occupied = pawns;
        int clash = 0;
        long x = idx;
        for (int i = n - 1; i >= 0; i--, x /= 64) {
            uint64_t m = 1ULL << (x % 64);
            clash |= (occupied & m) != 0;
            occupied |= m;
            colour[pieces[i] >> 3] |= m;
            type[pieces[i] & 7] |= m;
        }
        Pos p = {.white = colour[0], .black = colour[1], .kings = type[6], .queens = type[5],
                 .rooks = type[4], .bishops = type[3], .knights = type[2], .pawns = type[1],
                 .rule50 = 0, .ep = 0, .turn = x == 0};
        int success;
        is_quiet[idx] = 0;
        if (clash) { wdl[idx] = 5; continue; }
        if (!is_valid(&p)) { wdl[idx] = 6; continue; }
        int v = probe_wdl(&p, &success);
        if (!success) { wdl[idx] = 7; failures++; continue; }
        wdl[idx] = (int8_t)(v + 2);
        is_quiet[idx] = (uint8_t)quiet(&p);
    }
    return failures;
}
