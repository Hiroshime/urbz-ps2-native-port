#pragma once
#include <array>
#include <bit>
#include <cstdint>
#include <cstdio>
#include <span>
#include <stdexcept>
#include <string>

namespace ps2::net {
using Digest = std::array<std::uint8_t, 32>;

class Sha256 {
    std::array<std::uint32_t, 8> h{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    std::array<std::uint8_t, 64> block{};
    std::uint64_t length = 0;
    std::size_t used = 0;
    void compress() {
        static constexpr std::uint32_t k[] = {
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        std::uint32_t w[64];
        for (unsigned i=0;i<16;++i) w[i]=(std::uint32_t(block[i*4])<<24)|(std::uint32_t(block[i*4+1])<<16)|(std::uint32_t(block[i*4+2])<<8)|block[i*4+3];
        for (unsigned i=16;i<64;++i) {
            const auto a=w[i-15], b=w[i-2];
            w[i]=w[i-16]+(std::rotr(a,7)^std::rotr(a,18)^(a>>3))+w[i-7]+(std::rotr(b,17)^std::rotr(b,19)^(b>>10));
        }
        auto [a,b,c,d,e,f,g,v]=h;
        for (unsigned i=0;i<64;++i) {
            const auto t1=v+(std::rotr(e,6)^std::rotr(e,11)^std::rotr(e,25))+((e&f)^(~e&g))+k[i]+w[i];
            const auto t2=(std::rotr(a,2)^std::rotr(a,13)^std::rotr(a,22))+((a&b)^(a&c)^(b&c));
            v=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=v;
    }
public:
    void update(std::span<const std::uint8_t> bytes) {
        length+=bytes.size();
        for (auto byte:bytes) {
            block[used++]=byte;
            if (used==64) { compress();used=0; }
        }
    }
    Digest finish() {
        const auto bits=length*8;
        const std::uint8_t one=0x80, zero=0;
        update({&one,1});
        while (used!=56) update({&zero,1});
        std::uint8_t tail[8];
        for (unsigned i=0;i<8;++i) tail[7-i]=static_cast<std::uint8_t>(bits>>(i*8));
        update(tail);
        Digest out{};
        for (unsigned i=0;i<32;++i) out[i]=static_cast<std::uint8_t>(h[i/4]>>(24-8*(i%4)));
        return out;
    }
};

inline Digest hash(std::span<const std::uint8_t> bytes) { Sha256 h;h.update(bytes);return h.finish(); }
inline Digest hash_text(const std::string &text) { return hash({reinterpret_cast<const std::uint8_t*>(text.data()),text.size()}); }
inline Digest hash_file(std::FILE *file) {
    if (!file) throw std::runtime_error("cannot open identity file");
    Sha256 h;
    std::array<std::uint8_t, 65536> data{};
    for (;;) {
        const auto n=std::fread(data.data(),1,data.size(),file);
        h.update({data.data(),n});
        if (n<data.size()) {
            const bool bad=std::ferror(file)!=0;
            std::fclose(file);
            if (bad) throw std::runtime_error("cannot read identity file");
            return h.finish();
        }
    }
}
inline std::string hex(const Digest &d) {
    static constexpr char digits[]="0123456789abcdef";
    std::string s;
    for (auto b:d) { s+=digits[b>>4];s+=digits[b&15]; }
    return s;
}
}
