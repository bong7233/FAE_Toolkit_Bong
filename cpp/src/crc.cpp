#include "fae/crc.hpp"

namespace fae {

uint16_t crc16_modbus(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 0x0001) {
                crc = static_cast<uint16_t>((crc >> 1) ^ 0xA001);
            } else {
                crc = static_cast<uint16_t>(crc >> 1);
            }
        }
    }
    return crc;
}

uint16_t crc16_modbus(const std::vector<uint8_t>& data) {
    return crc16_modbus(data.data(), data.size());
}

std::vector<uint8_t> append_crc(const std::vector<uint8_t>& data) {
    const uint16_t crc = crc16_modbus(data);
    std::vector<uint8_t> out = data;
    out.push_back(static_cast<uint8_t>(crc & 0xFF));
    out.push_back(static_cast<uint8_t>((crc >> 8) & 0xFF));
    return out;
}

bool check_crc(const std::vector<uint8_t>& frame) {
    if (frame.size() < 3) {
        return false;
    }
    const std::vector<uint8_t> body(frame.begin(), frame.end() - 2);
    const uint16_t crc = crc16_modbus(body);
    const uint8_t lo = frame[frame.size() - 2];
    const uint8_t hi = frame[frame.size() - 1];
    return (crc & 0xFF) == lo && ((crc >> 8) & 0xFF) == hi;
}

}  // namespace fae
