// CRC-16/MODBUS — C++ port of fae_toolkit.core.crc.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace fae {

// CRC-16/MODBUS checksum (polynomial 0xA001, init 0xFFFF).
uint16_t crc16_modbus(const uint8_t* data, size_t len);
uint16_t crc16_modbus(const std::vector<uint8_t>& data);

// Append the little-endian CRC (Modbus wire order) to a copy of `data`.
std::vector<uint8_t> append_crc(const std::vector<uint8_t>& data);

// True if the last two bytes of `frame` are a valid Modbus CRC.
bool check_crc(const std::vector<uint8_t>& frame);

}  // namespace fae
