/*
 * A thin layer over Fathom (../fathom) for chesslab/tablebase.py: single Syzygy probes, and the
 * enumeration of every placement of one material signature, in parallel (OpenMP).
 */
#include "tbprobe.c"

int fathom_init(const char *path) { return tb_init(path) ? (int)TB_LARGEST : -1; }

static int make_pos(Pos *p, uint64_t w, uint64_t b, uint64_t k, uint64_t q, uint64_t r,
                    uint64_t bi, uint64_t n, uint64_t pa, int white_to_move) {
    *p = (Pos){.white = w, .black = b, .kings = k, .queens = q, .rooks = r, .bishops = bi,
               .knights = n, .pawns = pa, .rule50 = 0, .ep = 0, .turn = white_to_move != 0};
    return is_valid(p);
}

/* WDL from the side to move, -2..2 (Syzygy's five values); 99 = invalid position, 98 = failed. */
int fathom_wdl(uint64_t w, uint64_t b, uint64_t k, uint64_t q, uint64_t r, uint64_t bi,
               uint64_t n, uint64_t pa, int white_to_move) {
    Pos p;
    int success;
    if (!make_pos(&p, w, b, k, q, r, bi, n, pa, white_to_move)) return 99;
    int v = probe_wdl(&p, &success);
    return success ? v : 98;
}

/* DTZ from the side to move (Syzygy's convention); 9999 = invalid position, 9998 = failed. */
int fathom_dtz(uint64_t w, uint64_t b, uint64_t k, uint64_t q, uint64_t r, uint64_t bi,
               uint64_t n, uint64_t pa, int white_to_move) {
    Pos p;
    int success;
    if (!make_pos(&p, w, b, k, q, r, bi, n, pa, white_to_move)) return 9999;
    int v = probe_dtz(&p, &success);
    return success ? v : 9998;
}

/*
 * Write one code per index of every placement of the given pieces, both sides to move:
 * 0..4 = WDL + 2 from the side to move, 5 = two pieces on one square, 6 = illegal (side not to
 * move in check, or a pawn on rank 1 or 8), 7 = probe failed.
 * pieces[i] = colour * 8 + type (type 1 P, 2 N, 3 B, 4 R, 5 Q, 6 K; colour 0 White, 1 Black).
 * Index, most significant first: side to move (0 White), then the square of each piece. Each
 * piece takes 64 squares, a pawn 48 (ranks 2-7), the first pawn 24 (files a-d, ranks 2-7:
 * positions with it on files e-h are the mirror images). Returns the number of failed probes.
 */
long fathom_dump(int npieces, const int *pieces, int8_t *out) {
    int radix[8];
    long total = 2;
    for (int i = 0, pawns = 0; i < npieces; i++) {
        radix[i] = (pieces[i] & 7) != 1 ? 64 : pawns++ ? 48 : 24;
        total *= radix[i];
    }
    long failures = 0;
    #pragma omp parallel for schedule(dynamic, 4096) reduction(+:failures)
    for (long idx = 0; idx < total; idx++) {
        long x = idx;
        int sq[8];
        for (int i = npieces - 1; i >= 0; i--) {
            int s = (int)(x % radix[i]);
            x /= radix[i];
            sq[i] = radix[i] == 24 ? 8 + s / 4 * 8 + s % 4 : radix[i] == 48 ? 8 + s : s;
        }
        uint64_t occupied = 0, colour[2] = {0, 0}, type[7] = {0};
        int clash = 0;
        for (int i = 0; i < npieces; i++) {
            uint64_t m = 1ULL << sq[i];
            clash |= (occupied & m) != 0;
            occupied |= m;
            colour[pieces[i] >> 3] |= m;
            type[pieces[i] & 7] |= m;
        }
        Pos p;
        int success;
        if (clash) { out[idx] = 5; continue; }
        if (!make_pos(&p, colour[0], colour[1], type[6], type[5], type[4], type[3], type[2], type[1], x == 0)) {
            out[idx] = 6;
            continue;
        }
        int v = probe_wdl(&p, &success);
        if (success) out[idx] = (int8_t)(v + 2);
        else { out[idx] = 7; failures++; }
    }
    return failures;
}
