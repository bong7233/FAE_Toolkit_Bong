#include "fae/modbus.hpp"

#include "fae/crc.hpp"

namespace fae::modbus {

std::vector<uint8_t> build_read_holding_registers(uint8_t unit, uint16_t start, uint16_t count) {
    const std::vector<uint8_t> body = {
        unit,
        READ_HOLDING_REGISTERS,
        static_cast<uint8_t>(start >> 8),
        static_cast<uint8_t>(start & 0xFF),
        static_cast<uint8_t>(count >> 8),
        static_cast<uint8_t>(count & 0xFF),
    };
    return fae::append_crc(body);
}

}  // namespace fae::modbus
