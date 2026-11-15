#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace ps2 {
struct PadState {
    std::uint16_t buttons = 0;
    std::uint8_t axes[4] = {128, 128, 128, 128};  // right x/y, left x/y
    std::uint8_t l2 = 255, r2 = 255;
    bool connected = false;
    bool operator==(const PadState &other) const {
        return buttons == other.buttons && std::equal(std::begin(axes), std::end(axes), std::begin(other.axes)) &&
               l2 == other.l2 && r2 == other.r2 && connected == other.connected;
    }
};
using PadFrame = std::array<PadState, 2>;
}
