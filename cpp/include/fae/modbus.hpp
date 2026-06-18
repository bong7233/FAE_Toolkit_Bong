// Minimal Modbus-RTU framing — C++ port of fae_toolkit.protocols.modbus.
#pragma once

#include <cstdint>
#include <vector>

namespace fae::modbus {

constexpr uint8_t READ_HOLDING_REGISTERS = 0x03;
constexpr uint8_t READ_INPUT_REGISTERS = 0x04;
constexpr uint8_t WRITE_SINGLE_REGISTER = 0x06;

// Build a CRC-terminated "Read Holding Registers" request frame.
std::vector<uint8_t> build_read_holding_registers(uint8_t unit, uint16_t start, uint16_t count);

}  // namespace fae::modbus
