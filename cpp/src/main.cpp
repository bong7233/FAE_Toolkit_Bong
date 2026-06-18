// fae_crc — a small field utility: compute the CRC-16/MODBUS of a byte
// sequence and print the framed message. Handy when hand-checking a protocol
// capture against a device manual.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "fae/crc.hpp"
#include "fae/modbus.hpp"

namespace {

bool parse_hex_byte(const std::string& token, uint8_t& out) {
    std::string s = token;
    if (s.size() > 2 && s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
        s = s.substr(2);
    }
    if (s.empty() || s.size() > 2) {
        return false;
    }
    char* end = nullptr;
    long value = std::strtol(s.c_str(), &end, 16);
    if (*end != '\0' || value < 0 || value > 255) {
        return false;
    }
    out = static_cast<uint8_t>(value);
    return true;
}

void print_bytes(const std::vector<uint8_t>& bytes) {
    for (uint8_t b : bytes) {
        std::printf("%02X ", b);
    }
    std::printf("\n");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::printf("fae_crc - compute CRC-16/MODBUS for a sequence of bytes\n");
        std::printf("usage: fae_crc <hexbyte> [hexbyte ...]\n");
        std::printf("example: fae_crc 01 03 00 00 00 0C\n\n");
        auto demo = fae::modbus::build_read_holding_registers(1, 0, 12);
        std::printf("demo read-holding-registers(unit=1, start=0, count=12): ");
        print_bytes(demo);
        return 0;
    }

    std::vector<uint8_t> bytes;
    for (int i = 1; i < argc; ++i) {
        uint8_t b = 0;
        if (!parse_hex_byte(argv[i], b)) {
            std::printf("error: '%s' is not a hex byte (00..FF)\n", argv[i]);
            return 2;
        }
        bytes.push_back(b);
    }

    const uint16_t crc = fae::crc16_modbus(bytes);
    std::printf("CRC16/MODBUS = 0x%04X  (lo=0x%02X hi=0x%02X)\n", crc, crc & 0xFF,
                (crc >> 8) & 0xFF);
    std::printf("frame = ");
    print_bytes(fae::append_crc(bytes));
    return 0;
}
