// Socket/protocol tests with deterministic synthetic controllers, no game data.
#include "netplay.hpp"
#include <cstdio>
#include <cstdlib>
#include <string>

using namespace ps2;

PadState sample(std::uint64_t frame, unsigned player) {
    PadState p;
    p.connected = true;
    if (!frame) { p.l2 = p.r2 = 0; return p; }
    p.buttons = static_cast<std::uint16_t>(frame * 17 + player * 100);
    for (unsigned a = 0; a < 4; ++a) p.axes[a] = static_cast<std::uint8_t>(frame * 3 + player * 10 + a);
    p.l2 = static_cast<std::uint8_t>(frame + player); p.r2 = static_cast<std::uint8_t>(frame * 2 + player);
    return p;
}

int main(int argc, char **argv) {
    std::setvbuf(stderr, nullptr, _IONBF, 0);
    if (argc == 2 && std::string(argv[1]) == "--self-test") {
        const auto verify = [](const std::string &text, const std::string &expected) { return net::hex(net::hash_text(text)) == expected; };
        const bool okay = verify("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") &&
            verify("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") &&
            verify(std::string(1000000, 'a'), "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
        std::puts(okay ? "SHA-256 vectors passed" : "SHA-256 vectors FAILED");
        return okay ? 0 : 1;
    }
    if (argc == 3 && std::string(argv[1]) == "--hash-file") {
        std::puts(net::hex(net::hash_file(std::fopen(argv[2], "rb"))).c_str());
        return 0;
    }
    net::Config config;
    config.bind_address = "127.0.0.1";
    config.address = "127.0.0.1";
    config.timeout_ms = 3000;
    unsigned frames = 120, bad_check = 0, drop = 0;
    bool bad_game = false, bad_save = false, reject_card = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--host") config.hosting = true;
        else if (a == "--port" && i + 1 < argc) config.port = static_cast<std::uint16_t>(std::stoul(argv[++i]));
        else if (a == "--delay" && i + 1 < argc) config.delay = std::stoul(argv[++i]);
        else if (a == "--frames" && i + 1 < argc) frames = std::stoul(argv[++i]);
        else if (a == "--timeout" && i + 1 < argc) config.timeout_ms = std::stoul(argv[++i]);
        else if (a == "--bad-check" && i + 1 < argc) bad_check = std::stoul(argv[++i]);
        else if (a == "--drop" && i + 1 < argc) drop = std::stoul(argv[++i]);
        else if (a == "--bad-game") bad_game = true;
        else if (a == "--sync-card") config.sync_card = true;
        else if (a == "--bad-save") bad_save = true;
        else if (a == "--reject-card") reject_card = true;
        else if (a == "--secure") config.secure = true;
        else return 2;
    }
    if (const char *key = std::getenv("URBZ_NET_KEY")) config.session_key = key;
    net::Identity identity;
    identity.program = net::hash_text(bad_game ? "another game" : "same game");
    identity.initial_digest = 123;
    identity.rtc = 1700000000;
    net::CardSync card;
    if (config.sync_card) {
        card.image.resize(net::card_bytes);
        for (std::size_t i = 0; i < card.image.size(); ++i) card.image[i] = static_cast<std::uint8_t>(i * 13 + (config.hosting ? 17 : 99));
        identity.card = net::hash(card.image);
        card.install = [&](std::span<const std::uint8_t> image) {
            if (reject_card) throw std::runtime_error("test: card installation rejected");
            for (std::size_t i = 0; i < image.size(); ++i)
                if (image[i] != static_cast<std::uint8_t>(i * 13 + 17)) throw std::runtime_error("wrong shared card content");
            card.image.assign(image.begin(), image.end());
            std::puts("shared card content verified");
        };
    }
    net::Session session;
    if (!session.start(config, identity, {}, {}, config.sync_card ? &card : nullptr)) return 1;
    for (std::uint64_t f = 1; f <= frames; ++f) {
        if (f == drop) return 7;  // Destructor closes the peer's stream.
        PadFrame pads{sample(f, config.hosting ? 0 : 1), {}};
        if (!session.exchange(f, pads, f + 1000 + (f == bad_check ? 1 : 0))) return 1;
        const auto captured = f > config.delay ? f - config.delay : 0;
        if (!(pads[0] == sample(captured, 0)) || !(pads[1] == sample(captured, 1))) {
            std::fprintf(stderr, "wrong player mapping at frame %llu\n", static_cast<unsigned long long>(f));
            return 3;
        }
    }
    if (bad_save && !card.image.empty()) card.image[17] ^= 1;
    return session.finish(frames, config.sync_card ? net::hash(card.image) : net::Digest{}) ? 0 : 1;
}
