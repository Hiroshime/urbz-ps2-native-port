#pragma once
#include "ps2/input.hpp"
#include "sha256.hpp"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace ps2::net {
struct Config {
    bool hosting = false;
    std::string address, bind_address = "0.0.0.0";
    std::uint16_t port = 0;
    unsigned delay = 3, timeout_ms = 60000;
    bool sync_card = false;
    bool secure = false;
    std::string session_key;  // Random hex key, never placed on the command line.
};
struct Identity {
    Digest runtime{}, program{}, disc{}, snapshot{}, card{}, settings{};
    std::uint64_t first_frame = 0, rtc = 0, initial_digest = 0;
    unsigned rate = 50, language = 1;
};
inline constexpr std::size_t card_bytes = 16384 * 528;
struct CardSync {
    std::vector<std::uint8_t> image;
    // Called only after peer compatibility and the complete transfer are checked.
    // Throw on failure; Ready is sent only after installation has succeeded.
    std::function<void(std::span<const std::uint8_t>)> install;
};

class Session {
public:
    Session();
    ~Session();
    Session(const Session &) = delete;
    Session &operator=(const Session &) = delete;
    bool start(const Config &, Identity &, std::function<void()> pump = {}, std::function<bool()> cancelled = {}, CardSync *card = nullptr);
    bool exchange(std::uint64_t frame, PadFrame &, std::uint64_t digest);
    bool finish(std::uint64_t frame, const Digest &card = {});
    bool failed() const;
    const std::string &error() const;
private:
    struct Impl;
    std::unique_ptr<Impl> p;
};
}
