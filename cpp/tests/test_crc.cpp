// Dependency-free unit tests for the C++ CRC / Modbus core, registered with
// CTest. Mirrors the Python tests so both languages are checked the same way.

#include <cstdint>
#include <cstdio>
#include <vector>

#include "fae/crc.hpp"
#include "fae/modbus.hpp"

namespace {
int g_failures = 0;
}

#define CHECK(cond)                                              \
    do {                                                         \
        if (!(cond)) {                                           \
            std::printf("FAIL line %d: %s\n", __LINE__, #cond);  \
            ++g_failures;                                        \
        }                                                        \
    } while (0)

int main() {
    // Standard CRC-16/MODBUS catalogue check value for "123456789".
    const std::vector<uint8_t> check = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    CHECK(fae::crc16_modbus(check) == 0x4B37);

    // append/check round-trip.
    auto frame = fae::append_crc({0x01, 0x03, 0x00, 0x00, 0x00, 0x0C});
    CHECK(frame.size() == 8);
    CHECK(fae::check_crc(frame));

    // corruption is detected.
    frame[2] ^= 0xFF;
    CHECK(!fae::check_crc(frame));

    // Modbus request builder produces a valid frame.
    auto request = fae::modbus::build_read_holding_registers(1, 0, 12);
    CHECK(request.size() == 8);
    CHECK(request[0] == 0x01);
    CHECK(request[1] == fae::modbus::READ_HOLDING_REGISTERS);
    CHECK(fae::check_crc(request));

    if (g_failures == 0) {
        std::printf("All C++ tests passed\n");
        return 0;
    }
    std::printf("%d C++ test(s) failed\n", g_failures);
    return 1;
}
