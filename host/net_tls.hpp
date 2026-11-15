#pragma once
#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <string>

namespace ps2::net {
// TLS 1.2 with a random pre-shared session key and ephemeral DH. No certificates
// or external accounts are needed. Framing remains in netplay.cpp.
class TlsStream {
public:
    using Wait = std::function<void(bool writing)>;
    TlsStream(bool server, std::intptr_t socket, const std::string &hex_key);
    ~TlsStream();
    void handshake(const Wait &);
    std::size_t read(std::span<std::uint8_t>, const Wait &);
    std::size_t write(std::span<const std::uint8_t>, const Wait &);
    bool pending() const;
private:
    struct Impl;
    std::unique_ptr<Impl> p;
};
bool valid_session_key(const std::string &);
}
