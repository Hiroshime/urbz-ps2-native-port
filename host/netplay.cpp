#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/tcp.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>
#endif
#include "netplay.hpp"
#include "net_tls.hpp"
#include <chrono>
#include <climits>
#include <cstdio>
#include <ctime>
#include <limits>
#include <map>
#include <stdexcept>
#include <thread>
#include <vector>

namespace ps2::net {
namespace {
using Clock = std::chrono::steady_clock;
#ifdef _WIN32
using Socket = SOCKET;
constexpr auto bad_socket = INVALID_SOCKET;
void close_socket(Socket s) { if (s != bad_socket) closesocket(s); }
int socket_error() { return WSAGetLastError(); }
bool pending(int e) { return e == WSAEWOULDBLOCK || e == WSAEINPROGRESS; }
#else
using Socket = int;
constexpr auto bad_socket = -1;
void close_socket(Socket s) { if (s != bad_socket) close(s); }
int socket_error() { return errno; }
bool pending(int e) { return e == EWOULDBLOCK || e == EAGAIN || e == EINPROGRESS || e == EINTR; }
#endif
void nonblocking(Socket socket) {
#ifdef _WIN32
    u_long one = 1;
    if (ioctlsocket(socket, FIONBIO, &one)) throw std::runtime_error("cannot configure socket");
#else
    const int flags = fcntl(socket, F_GETFL);
    if (flags < 0 || fcntl(socket, F_SETFL, flags | O_NONBLOCK) < 0) throw std::runtime_error("cannot configure socket");
#endif
}

struct Writer {
    std::vector<std::uint8_t> data;
    void number(std::uint64_t n, unsigned bytes) {
        for (unsigned i = bytes; i; --i) data.push_back(static_cast<std::uint8_t>(n >> (8 * (i - 1))));
    }
    void digest(const Digest &d) { data.insert(data.end(), d.begin(), d.end()); }
};
struct Reader {
    std::span<const std::uint8_t> data;
    std::size_t at = 0;
    std::uint64_t number(unsigned bytes) {
        if (bytes > 8 || bytes > data.size() - at) throw std::runtime_error("truncated network message");
        std::uint64_t n = 0;
        while (bytes--) n = (n << 8) | data[at++];
        return n;
    }
    Digest digest() {
        Digest d;
        for (auto &v : d) v = static_cast<std::uint8_t>(number(1));
        return d;
    }
    void end() { if (at != data.size()) throw std::runtime_error("unexpected network message size"); }
};
constexpr std::uint64_t magic = 0x5552425a4e455431ull;  // URBZNET1
constexpr unsigned protocol = 3, check_every = 30, card_chunk = 65536;
enum Message { Hello = 1, Input = 2, Stop = 3, Ready = 4, CardBegin = 5, CardData = 6 };
PadState neutral() { PadState p; p.connected = true; p.l2 = p.r2 = 0; return p; }
}

struct Session::Impl {
    Config config;
    Identity identity;
    CardSync *card_sync = nullptr;
    Digest end_card{};
    Socket socket = bad_socket, listener = bad_socket;
    std::unique_ptr<TlsStream> tls;
    Clock::time_point auth_deadline;
    std::function<void()> pump;
    std::function<bool()> cancelled;
    std::string why;
    bool ending = false, peer_stopped = false, started = false;
    std::uint64_t frame = 0, last_remote = 0, stopped_frame = 0, checks = 0, frames = 0;
    double waited_ms = 0;
    std::map<std::uint64_t, PadState> local, remote;
    std::map<std::uint64_t, std::uint64_t> local_checks, remote_checks;
    ~Impl() { tls.reset(); close_socket(socket); close_socket(listener); }
    void fail(const std::string &message) { throw std::runtime_error(message); }
    void tick() {
        if (pump) pump();
        if (!ending && cancelled && cancelled()) fail("session cancelled");
    }
    bool available(Socket s, bool writing, Clock::time_point deadline, bool once = false) {
#ifndef _WIN32
        if (s < 0 || s >= FD_SETSIZE) fail("socket descriptor exceeds the select limit");
#endif
        do {
            tick();
            if (!once && Clock::now() >= deadline) fail("timeout waiting for the other player");
            fd_set set; FD_ZERO(&set); FD_SET(s, &set);
            timeval wait{0, once ? 0 : 20000};
            const int result = select(static_cast<int>(s + 1), writing ? nullptr : &set, writing ? &set : nullptr, nullptr, &wait);
            if (result > 0) return true;
            if (result < 0 && !pending(socket_error())) fail("socket wait failed");
            if (once) return false;
        } while (Clock::now() < deadline);
        fail("timeout waiting for the other player");
        return false;
    }
    Clock::time_point deadline() const { return Clock::now() + std::chrono::milliseconds(config.timeout_ms); }
    void write_all(std::span<const std::uint8_t> bytes) {
        const auto end = deadline();
        while (!bytes.empty()) {
            if (tls) {
                const auto count = tls->write(bytes, [&](bool writing) { available(socket, writing, end); });
                bytes = bytes.subspan(count);
                continue;
            }
            available(socket, true, end);
#ifdef _WIN32
            const int n = ::send(socket, reinterpret_cast<const char*>(bytes.data()), static_cast<int>(bytes.size()), 0);
#else
            const auto n = ::send(socket, bytes.data(), bytes.size(), MSG_NOSIGNAL);
#endif
            if (n > 0) bytes = bytes.subspan(static_cast<std::size_t>(n));
            else if (n == 0 || !pending(socket_error())) fail("the other player disconnected while sending");
        }
    }
    void read_all(std::span<std::uint8_t> bytes) {
        const auto end = deadline();
        while (!bytes.empty()) {
            if (tls) {
                const auto count = tls->read(bytes, [&](bool writing) { available(socket, writing, end); });
                bytes = bytes.subspan(count);
                continue;
            }
            available(socket, false, end);
#ifdef _WIN32
            const int n = recv(socket, reinterpret_cast<char*>(bytes.data()), static_cast<int>(bytes.size()), 0);
#else
            const auto n = recv(socket, bytes.data(), bytes.size(), 0);
#endif
            if (n > 0) bytes = bytes.subspan(static_cast<std::size_t>(n));
            else if (n == 0 || !pending(socket_error())) fail("the other player disconnected while receiving");
        }
    }
    void send(const Writer &message) {
        Writer head; head.number(message.data.size(), 4);
        head.data.insert(head.data.end(), message.data.begin(), message.data.end());
        write_all(head.data);
    }
    std::vector<std::uint8_t> receive(std::size_t limit = 512) {
        std::array<std::uint8_t, 4> head;
        read_all(head);
        Reader r{head};
        const auto size = r.number(4);
        if (size < 4 || size > limit) fail("invalid network message length");
        std::vector<std::uint8_t> data(static_cast<std::size_t>(size));
        read_all(data);
        return data;
    }
    void connect_peer() {
#ifdef _WIN32
        static const bool winsock = [] { WSADATA data; return WSAStartup(MAKEWORD(2, 2), &data) == 0; }();
        if (!winsock) fail("cannot start Windows sockets");
#endif
        addrinfo hints{}, *addresses = nullptr;
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_STREAM;
        const auto address = config.hosting ? config.bind_address : config.address;
        if (getaddrinfo(address.c_str(), std::to_string(config.port).c_str(), &hints, &addresses)) fail("cannot resolve network address");
        const std::unique_ptr<addrinfo, decltype(&freeaddrinfo)> resolved(addresses, &freeaddrinfo);
        // IPv4 is the deliberately small initial LAN scope.
        socket = ::socket(addresses->ai_family, addresses->ai_socktype, addresses->ai_protocol);
        if (socket == bad_socket) fail("cannot create socket");
        nonblocking(socket);
        if (config.hosting) {
            const int one = 1;
#ifndef _WIN32
            setsockopt(socket, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
#else
            setsockopt(socket, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, reinterpret_cast<const char*>(&one), sizeof(one));
#endif
            const int bound = bind(socket, addresses->ai_addr, static_cast<int>(addresses->ai_addrlen));
            if (bound || listen(socket, 1)) fail("cannot listen on the requested port");
            listener = socket;
            socket = bad_socket;
            std::fprintf(stderr, "[net] waiting on %s:%u\n", address.c_str(), config.port);
            auth_deadline = deadline();
            available(listener, false, auth_deadline);
            socket = accept(listener, nullptr, nullptr);
            if (socket == bad_socket) fail("cannot accept connection");
            if (!config.secure) { close_socket(listener); listener = bad_socket; }
            nonblocking(socket);
        } else {
            const auto end = deadline();
            std::fprintf(stderr, "[net] connecting to %s:%u\n", address.c_str(), config.port);
            for (;;) {
                const int result = connect(socket, addresses->ai_addr, static_cast<int>(addresses->ai_addrlen));
                int error = result == 0 ? 0 : socket_error();
                if (result == 0 || pending(error)) {
                    available(socket, true, end);
                    error = 0;
#ifdef _WIN32
                    int size = sizeof(error);
                    if (getsockopt(socket, SOL_SOCKET, SO_ERROR, reinterpret_cast<char*>(&error), &size)) error = socket_error();
#else
                    socklen_t size = sizeof(error);
                    if (getsockopt(socket, SOL_SOCKET, SO_ERROR, &error, &size)) error = socket_error();
#endif
                }
                if (!error) break;
                close_socket(socket); socket = bad_socket;
                if (Clock::now() >= end) fail("timeout connecting to the host");
                const auto retry = std::min(end, Clock::now() + std::chrono::milliseconds(200));
                while (Clock::now() < retry) { tick(); std::this_thread::sleep_for(std::chrono::milliseconds(10)); }
                socket = ::socket(addresses->ai_family, addresses->ai_socktype, addresses->ai_protocol);
                if (socket == bad_socket) fail("cannot create socket");
                nonblocking(socket);
            }
        }
        const int one = 1;
        setsockopt(socket, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&one), sizeof(one));
    }
    void secure_peer() {
        if (!config.secure) return;
        for (;;) {
            const auto end = std::min(config.hosting ? auth_deadline : deadline(), Clock::now() + std::chrono::seconds(5));
            try {
                tls = std::make_unique<TlsStream>(config.hosting, static_cast<std::intptr_t>(socket), config.session_key);
                tls->handshake([&](bool writing) { available(socket, writing, end); });
                close_socket(listener); listener = bad_socket;
                std::fprintf(stderr, "[net] authenticated encrypted connection: TLS 1.2 DHE-PSK/AES-128-GCM\n");
                return;
            } catch (const std::exception &) {
                tls.reset();
                if (!config.hosting) throw;
                close_socket(socket); socket = bad_socket;
                std::fprintf(stderr, "[net] unauthenticated peer rejected; waiting for your friend\n");
                if (Clock::now() >= auth_deadline) throw std::runtime_error("timeout waiting for an authenticated player");
                available(listener, false, auth_deadline);
                socket = accept(listener, nullptr, nullptr);
                if (socket == bad_socket) fail("cannot accept connection");
                nonblocking(socket);
                const int one = 1;
                setsockopt(socket, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&one), sizeof(one));
            }
        }
    }
    bool input_available() {
        return (tls && tls->pending()) || available(socket, false, deadline(), true);
    }
    void handshake() {
        Writer hello;
        hello.number(Hello, 4); hello.number(magic, 8); hello.number(protocol, 4);
        hello.number(config.hosting ? 0 : 1, 1); hello.number(config.delay, 4);
        hello.number(config.sync_card ? 1 : 0, 1);
        hello.number(config.secure ? 1 : 0, 1);
        hello.number(identity.rate, 4); hello.number(identity.language, 4);
        hello.number(identity.first_frame, 8); hello.number(identity.rtc, 8); hello.number(identity.initial_digest, 8);
        for (const auto &d : {identity.runtime, identity.program, identity.disc, identity.snapshot, identity.card, identity.settings}) hello.digest(d);
        send(hello);
        const auto bytes = receive(); Reader r{bytes};
        if (r.number(4) != Hello || r.number(8) != magic || r.number(4) != protocol) fail("incompatible netplay protocol");
        if (r.number(1) != (config.hosting ? 1u : 0u)) fail("both players selected the same role");
        if (r.number(4) != config.delay) fail("input delay differs between players");
        if (r.number(1) != (config.sync_card ? 1u : 0u)) fail("memory card synchronization mode differs");
        if (r.number(1) != (config.secure ? 1u : 0u)) fail("connection protection mode differs");
        if (r.number(4) != identity.rate || r.number(4) != identity.language) fail("video rate or language differs");
        if (r.number(8) != identity.first_frame) fail("initial frame differs");
        const auto peer_rtc = r.number(8);
        if (r.number(8) != identity.initial_digest) fail("initial EE state differs");
        const char *names[] = {"runtime build", "game executable", "disc content", "initial snapshot", "memory card", "simulation settings (including internal resolution and 2D filtering)"};
        const Digest own[] = {identity.runtime, identity.program, identity.disc, identity.snapshot, identity.card, identity.settings};
        for (unsigned i = 0; i < 6; ++i) {
            const auto peer = r.digest();
            if (peer != own[i] && !(i == 4 && config.sync_card)) fail(std::string(names[i]) + " differs between players");
        }
        r.end();
        if (!config.hosting) {
            if (identity.rtc && identity.rtc != peer_rtc) fail("explicit RTC differs from the host");
            identity.rtc = peer_rtc;
        } else if (peer_rtc && peer_rtc != identity.rtc) fail("explicit RTC differs from the client");
        if (config.sync_card) sync_memory_card();
        Writer ready; ready.number(Ready, 4); ready.number(identity.rtc, 8); ready.digest(identity.card); send(ready);
        const auto answer = receive(); Reader a{answer};
        if (a.number(4) != Ready || a.number(8) != identity.rtc || a.digest() != identity.card) fail("session clock or memory card negotiation failed");
        a.end();
        frame = last_remote = identity.first_frame;
        for (unsigned d = 1; d <= config.delay; ++d) local[frame+d] = remote[frame+d] = neutral();
        std::fprintf(stderr, "[net] connected as player %u, first frame %llu, %u Hz, delay %u, RTC %llu\n", config.hosting ? 1 : 2,
                     static_cast<unsigned long long>(frame), identity.rate, config.delay, static_cast<unsigned long long>(identity.rtc));
        started = true;
    }
    void sync_memory_card() {
        std::vector<std::uint8_t> image;
        Digest expected{};
        if (config.hosting) {
            image = card_sync->image;
            expected = hash(image);
            Writer begin; begin.number(CardBegin, 4); begin.number(image.size(), 4); begin.digest(expected); send(begin);
            for (std::size_t at = 0; at < image.size(); at += card_chunk) {
                Writer chunk; chunk.number(CardData, 4); chunk.number(at, 4);
                const auto n = std::min<std::size_t>(card_chunk, image.size() - at);
                chunk.data.insert(chunk.data.end(), image.begin() + at, image.begin() + at + n);
                send(chunk);
            }
        } else {
            const auto bytes = receive(); Reader begin{bytes};
            if (begin.number(4) != CardBegin || begin.number(4) != card_bytes) fail("invalid shared memory card size");
            expected = begin.digest(); begin.end();
            image.reserve(card_bytes);
            while (image.size() < card_bytes) {
                const auto chunk = receive(card_chunk + 8); Reader data{chunk};
                if (data.number(4) != CardData || data.number(4) != image.size()) fail("invalid shared memory card chunk");
                const auto n = std::min<std::size_t>(card_chunk, card_bytes - image.size());
                if (chunk.size() != n + 8) fail("invalid shared memory card chunk size");
                image.insert(image.end(), chunk.begin() + 8, chunk.end());
            }
            if (hash(image) != expected) fail("shared memory card checksum mismatch");
        }
        card_sync->install(image);
        identity.card = expected;
        std::fprintf(stderr, "[net] shared memory card synchronized: %s\n", hex(expected).c_str());
    }
    void compare(std::uint64_t at) {
        const auto a = local_checks.find(at), b = remote_checks.find(at);
        if (a == local_checks.end() || b == remote_checks.end()) return;
        if (a->second != b->second) fail("DESYNC at frame " + std::to_string(at));
        ++checks;
        local_checks.erase(a); remote_checks.erase(b);
    }
    void process() {
        const auto bytes = receive(); Reader r{bytes};
        const auto kind = r.number(4);
        if (kind == Stop) {
            stopped_frame = r.number(8); end_card = r.digest(); r.end(); peer_stopped = true; return;
        }
        if (kind != Input || peer_stopped) fail("unexpected network message");
        const auto captured = r.number(8), target = r.number(8);
        if (captured != last_remote + 1 || captured > frame + 512 || captured > UINT64_MAX - config.delay || target != captured + config.delay)
            fail("invalid or out-of-order input frame");
        last_remote = captured;
        PadState pad;
        pad.buttons = static_cast<std::uint16_t>(r.number(2));
        for (auto &a : pad.axes) a = static_cast<std::uint8_t>(r.number(1));
        pad.l2 = static_cast<std::uint8_t>(r.number(1)); pad.r2 = static_cast<std::uint8_t>(r.number(1));
        if (r.number(1) != 1) fail("invalid connected controller state");
        pad.connected = true;
        const auto digest = r.number(8); r.end();
        if (remote.size() >= 1024 || remote_checks.size() >= 1024) fail("network input queue limit exceeded");
        if (!remote.emplace(target, pad).second) fail("duplicate input frame");
        if (captured % check_every == 0) { remote_checks[captured] = digest; compare(captured); }
        else if (digest) fail("unexpected checksum frame");
    }
    bool caught(const std::exception &e) {
        if (why.empty()) { why = e.what(); std::fprintf(stderr, "[net] stopped: %s\n", why.c_str()); }
        tls.reset();
        close_socket(socket); socket = bad_socket;
        close_socket(listener); listener = bad_socket;
        return false;
    }
};

Session::Session() : p(std::make_unique<Impl>()) {}
Session::~Session() = default;
bool Session::failed() const { return !p->why.empty(); }
const std::string &Session::error() const { return p->why; }

bool Session::start(const Config &config, Identity &identity, std::function<void()> pump, std::function<bool()> cancelled, CardSync *card) {
    try {
        if (!config.port || config.delay > 12 || config.timeout_ms < 100 || config.timeout_ms > 300000 || identity.first_frame > UINT64_MAX - 1024)
            throw std::runtime_error("invalid network configuration");
        if (config.sync_card && (!card || card->image.size() != card_bytes || !card->install))
            throw std::runtime_error("shared memory card is unavailable");
        if (config.secure && !valid_session_key(config.session_key)) throw std::runtime_error("invalid session key");
        p->config = config; p->identity = identity; p->pump = std::move(pump); p->cancelled = std::move(cancelled);
        p->card_sync = card;
        if (config.hosting && !p->identity.rtc) p->identity.rtc = static_cast<std::uint64_t>(std::time(nullptr));
        p->connect_peer(); p->secure_peer(); p->handshake(); p->card_sync = nullptr; identity = p->identity;
        return true;
    } catch (const std::exception &e) { return p->caught(e); }
}

bool Session::exchange(std::uint64_t frame, PadFrame &pads, std::uint64_t digest) {
    try {
        if (!p->started || failed() || frame != p->frame + 1 || frame > UINT64_MAX - p->config.delay) throw std::runtime_error("invalid local input frame");
        p->frame = frame;
        PadState own = pads[0];  // Each PC uses its keyboard/first physical controller.
        own.connected = true;
        const auto target = frame + p->config.delay;
        p->local[target] = own;
        Writer input; input.number(Input, 4); input.number(frame, 8); input.number(target, 8); input.number(own.buttons, 2);
        for (auto axis : own.axes) input.number(axis, 1);
        input.number(own.l2, 1); input.number(own.r2, 1); input.number(1, 1);
        input.number(frame % check_every == 0 ? digest : 0, 8);
        if (frame % check_every == 0) { p->local_checks[frame] = digest; p->compare(frame); }
        p->send(input);
        const auto begin = Clock::now();
        while (!p->remote.contains(frame)) {
            if (p->peer_stopped) throw std::runtime_error("the other player ended the session");
            p->process();
        }
        // Drain complete pending messages so checksum comparisons do not lag behind.
        while (!p->peer_stopped && p->input_available()) p->process();
        p->waited_ms += std::chrono::duration<double, std::milli>(Clock::now()-begin).count();
        const unsigned port = p->config.hosting ? 0 : 1;
        pads[port] = p->local.at(frame); pads[1-port] = p->remote.at(frame);
        p->local.erase(frame); p->remote.erase(frame); ++p->frames;
        return true;
    } catch (const std::exception &e) { return p->caught(e); }
}

bool Session::finish(std::uint64_t frame, const Digest &card) {
    try {
        if (failed() || !p->started) return false;
        p->ending = true;
        Writer stop; stop.number(Stop, 4); stop.number(frame, 8); stop.digest(card); p->send(stop);
        while (!p->peer_stopped) p->process();
        if (p->stopped_frame != frame || !p->local_checks.empty() || !p->remote_checks.empty()) throw std::runtime_error("players ended at different frames or with unchecked state");
        if (p->end_card != card) throw std::runtime_error("memory cards differ at session end");
        std::fprintf(stderr, "[net] complete: %llu frames, %llu state checks matched, %.1f ms waiting\n",
                     static_cast<unsigned long long>(p->frames), static_cast<unsigned long long>(p->checks), p->waited_ms);
        return true;
    } catch (const std::exception &e) { return p->caught(e); }
}
}
