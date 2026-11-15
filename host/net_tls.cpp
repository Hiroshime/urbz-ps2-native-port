#include "net_tls.hpp"
#include <openssl/crypto.h>
#include <openssl/err.h>
#include <openssl/ssl.h>
#include <climits>
#include <csignal>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace ps2::net {
namespace {
int hex_digit(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
constexpr char identity[] = "urbz-direct-v1";
}
bool valid_session_key(const std::string &key) {
    if (key.size() != 32 && key.size() != 64) return false;
    for (const char c : key) if (hex_digit(c) < 0) return false;
    return true;
}
struct TlsStream::Impl {
    std::unique_ptr<SSL_CTX, decltype(&SSL_CTX_free)> ctx{nullptr, &SSL_CTX_free};
    std::unique_ptr<SSL, decltype(&SSL_free)> ssl{nullptr, &SSL_free};
    std::vector<unsigned char> key;
    ~Impl() { if (!key.empty()) OPENSSL_cleanse(key.data(), key.size()); }
    void error(int result, const Wait &wait) {
        const int code = SSL_get_error(ssl.get(), result);
        if (code == SSL_ERROR_WANT_READ) { wait(false); return; }
        if (code == SSL_ERROR_WANT_WRITE) { wait(true); return; }
        if (code == SSL_ERROR_ZERO_RETURN) throw std::runtime_error("TLS peer disconnected");
        char detail[256] = {};
        const auto reason = ERR_get_error();
        if (reason) ERR_error_string_n(reason, detail, sizeof(detail));
        throw std::runtime_error(std::string("TLS connection/authentication failed; verify the session key") + (reason ? std::string(": ") + detail : ""));
    }
};
TlsStream::TlsStream(bool server, std::intptr_t socket, const std::string &key) : p(std::make_unique<Impl>()) {
#ifndef _WIN32
    // OpenSSL's socket BIO uses write(), unlike the raw path's MSG_NOSIGNAL.
    static const bool ignored = [] { std::signal(SIGPIPE, SIG_IGN); return true; }();
    (void)ignored;
#endif
    if (!valid_session_key(key)) throw std::runtime_error("session key must contain 32 or 64 hexadecimal characters");
    if (socket < 0 || socket > INT_MAX) throw std::runtime_error("socket exceeds the TLS descriptor limit");
    for (std::size_t i = 0; i < key.size(); i += 2) p->key.push_back(static_cast<unsigned char>((hex_digit(key[i]) << 4) | hex_digit(key[i+1])));
    p->ctx.reset(SSL_CTX_new(TLS_method()));
    if (!p->ctx) throw std::runtime_error("cannot initialize TLS");
    auto *ctx = p->ctx.get();
    SSL_CTX_set_security_level(ctx, 2);
    if (!SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION) || !SSL_CTX_set_max_proto_version(ctx, TLS1_2_VERSION) ||
        !SSL_CTX_set_cipher_list(ctx, "DHE-PSK-AES128-GCM-SHA256") || !SSL_CTX_set_dh_auto(ctx, 1))
        throw std::runtime_error("cannot configure TLS PSK");
    SSL_CTX_set_options(ctx, SSL_OP_NO_RENEGOTIATION | SSL_OP_NO_TICKET | SSL_OP_NO_COMPRESSION);
    SSL_CTX_set_session_cache_mode(ctx, SSL_SESS_CACHE_OFF);
    SSL_CTX_set_psk_client_callback(ctx, [](SSL *ssl, const char *, char *name, unsigned name_size, unsigned char *out, unsigned max) -> unsigned {
        const auto *self = static_cast<Impl*>(SSL_get_app_data(ssl));
        if (name_size < sizeof(identity) || max < self->key.size()) return 0;
        std::memcpy(name, identity, sizeof(identity));
        std::memcpy(out, self->key.data(), self->key.size());
        return static_cast<unsigned>(self->key.size());
    });
    SSL_CTX_set_psk_server_callback(ctx, [](SSL *ssl, const char *name, unsigned char *out, unsigned max) -> unsigned {
        const auto *self = static_cast<Impl*>(SSL_get_app_data(ssl));
        if (!name || std::strcmp(name, identity) || max < self->key.size()) return 0;
        std::memcpy(out, self->key.data(), self->key.size());
        return static_cast<unsigned>(self->key.size());
    });
    p->ssl.reset(SSL_new(ctx));
    if (!p->ssl || !SSL_set_fd(p->ssl.get(), static_cast<int>(socket))) throw std::runtime_error("cannot attach TLS socket");
    SSL_set_app_data(p->ssl.get(), p.get());
    if (server) SSL_set_accept_state(p->ssl.get()); else SSL_set_connect_state(p->ssl.get());
}
TlsStream::~TlsStream() = default;
void TlsStream::handshake(const Wait &wait) {
    for (;;) {
        ERR_clear_error();
        const int result = SSL_do_handshake(p->ssl.get());
        if (result == 1) return;
        p->error(result, wait);
    }
}
std::size_t TlsStream::read(std::span<std::uint8_t> bytes, const Wait &wait) {
    for (;;) {
        ERR_clear_error(); std::size_t count = 0;
        const int result = SSL_read_ex(p->ssl.get(), bytes.data(), bytes.size(), &count);
        if (result == 1) return count;
        p->error(result, wait);
    }
}
std::size_t TlsStream::write(std::span<const std::uint8_t> bytes, const Wait &wait) {
    for (;;) {
        ERR_clear_error(); std::size_t count = 0;
        const int result = SSL_write_ex(p->ssl.get(), bytes.data(), bytes.size(), &count);
        if (result == 1) return count;
        p->error(result, wait);
    }
}
bool TlsStream::pending() const { return SSL_pending(p->ssl.get()) > 0; }
}
