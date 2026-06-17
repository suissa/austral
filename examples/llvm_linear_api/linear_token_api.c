#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

// "Linear" token representation (single-owner by convention).
typedef struct {
  uint64_t value;
  uint64_t rounds;
} LinearToken;

static inline uint64_t rotl64(uint64_t x, int r) {
  return (x << r) | (x >> (64 - r));
}

// Compute-heavy mixing, intended to benefit from LLVM optimizations.
LinearToken generate_linear_token(const uint8_t* data, size_t len, uint64_t seed) {
  uint64_t s0 = seed ^ 0x9e3779b97f4a7c15ULL;
  uint64_t s1 = (seed << 1) ^ 0xbf58476d1ce4e5b9ULL;
  for (size_t i = 0; i < len; i++) {
    s0 ^= ((uint64_t)data[i] + 0x100000001b3ULL);
    s0 = rotl64(s0, 27) * 0x94d049bb133111ebULL;
    s1 ^= s0 + ((uint64_t)i * 0x9e3779b1ULL);
    s1 = rotl64(s1, 31) * 0xbf58476d1ce4e5b9ULL;
  }
  for (int r = 0; r < 2048; r++) {
    s0 ^= s1; s0 = rotl64(s0, 17) * 0x9e3779b97f4a7c15ULL;
    s1 ^= s0; s1 = rotl64(s1, 29) * 0x94d049bb133111ebULL;
  }
  LinearToken t = { s0 ^ s1, 2048 };
  return t;
}

// Data pipeline touching common primitive shapes: bytes -> ints -> aggregate -> linear token.
LinearToken transform_all_types(const char* input) {
  size_t len = strlen(input);
  uint8_t bytes[256];
  size_t n = len > 255 ? 255 : len;
  for (size_t i = 0; i < n; i++) bytes[i] = (uint8_t)input[i];

  int32_t acc_i32 = 0;
  uint64_t acc_u64 = 1469598103934665603ULL;
  double acc_f64 = 0.0;
  for (size_t i = 0; i < n; i++) {
    acc_i32 += (int32_t)bytes[i] * (int32_t)(i + 1);
    acc_u64 ^= (uint64_t)bytes[i];
    acc_u64 *= 1099511628211ULL;
    acc_f64 += (double)bytes[i] / (double)(i + 1);
  }

  uint64_t seed = acc_u64 ^ (uint64_t)(uint32_t)acc_i32 ^ (uint64_t)(acc_f64 * 1000000.0);
  return generate_linear_token(bytes, n, seed);
}

static void handle_client(int fd) {
  char buf[1024];
  ssize_t n = read(fd, buf, sizeof(buf)-1);
  if (n <= 0) return;
  buf[n] = '\0';

  // Protocol: TOKEN <payload>\n
  const char* payload = buf;
  if (strncmp(buf, "TOKEN ", 6) == 0) payload = buf + 6;
  char* nl = strchr((char*)payload, '\n');
  if (nl) *nl = '\0';

  LinearToken t = transform_all_types(payload);
  char out[256];
  int outn = snprintf(out, sizeof(out), "{\"token\":\"%016llx\",\"rounds\":%llu}\n",
      (unsigned long long)t.value,
      (unsigned long long)t.rounds);
  write(fd, out, (size_t)outn);
}

int main(int argc, char** argv) {
  int port = 9090;
  if (argc > 1) port = atoi(argv[1]);

  int server_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (server_fd < 0) { perror("socket"); return 1; }
  int opt = 1;
  setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = INADDR_ANY;
  addr.sin_port = htons((uint16_t)port);

  if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) { perror("bind"); return 1; }
  if (listen(server_fd, 128) < 0) { perror("listen"); return 1; }

  printf("linear-token-api listening on %d\n", port);
  fflush(stdout);
  while (1) {
    int cfd = accept(server_fd, NULL, NULL);
    if (cfd < 0) {
      if (errno == EINTR) continue;
      perror("accept");
      break;
    }
    handle_client(cfd);
    close(cfd);
  }
  close(server_fd);
  return 0;
}
