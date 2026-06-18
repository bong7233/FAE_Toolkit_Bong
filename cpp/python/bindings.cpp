// pybind11 bindings: expose the C++ protocol core to Python as `faecore`.
//
// Lets the Python package call the compiled CRC/Modbus implementation, proving
// the C++ and Python sides interoperate. Built only when FAE_BUILD_PYBIND=ON.

#include <pybind11/pybind11.h>

#include <cstdint>
#include <string>
#include <vector>

#include "fae/crc.hpp"
#include "fae/modbus.hpp"

namespace py = pybind11;

namespace {

uint16_t crc_from_bytes(const py::bytes& data) {
    const std::string s = data;
    const std::vector<uint8_t> v(s.begin(), s.end());
    return fae::crc16_modbus(v);
}

py::bytes build_read_holding_registers(uint8_t unit, uint16_t start, uint16_t count) {
    const auto frame = fae::modbus::build_read_holding_registers(unit, start, count);
    return py::bytes(reinterpret_cast<const char*>(frame.data()), frame.size());
}

}  // namespace

PYBIND11_MODULE(faecore, m) {
    m.doc() = "FAE Toolkit C++ protocol core (CRC-16/MODBUS + Modbus framing)";
    m.def("crc16_modbus", &crc_from_bytes, py::arg("data"),
          "CRC-16/MODBUS checksum of a bytes object.");
    m.def("build_read_holding_registers", &build_read_holding_registers, py::arg("unit"),
          py::arg("start"), py::arg("count"),
          "Build a CRC-terminated Modbus Read-Holding-Registers request frame.");
}
