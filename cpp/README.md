# FAE Toolkit — C++ core

A small, dependency-free C++17 port of the toolkit's protocol primitives
(CRC-16/MODBUS + Modbus-RTU framing), with a CMake build and CTest tests.

It exists to show the same protocol logic implemented in a compiled,
systems-level language and built cross-platform (GCC on Linux, MSVC on Windows)
in CI — the natural step up from a Delphi/Object-Pascal background. The bytes it
produces are identical to the Python implementation.

## Layout

```
cpp/
├── include/fae/   public headers (crc.hpp, modbus.hpp)
├── src/           crc.cpp, modbus.cpp, main.cpp (fae_crc CLI)
├── tests/         test_crc.cpp (CTest)
└── CMakeLists.txt
```

## Build & test

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --config Release
ctest --test-dir cpp/build -C Release --output-on-failure
```

## Utility

`fae_crc` computes the CRC-16/MODBUS of a byte sequence — handy when checking a
protocol capture against a device manual:

```bash
$ ./cpp/build/fae_crc 01 03 00 00 00 0C
CRC16/MODBUS = 0xCF45  (lo=0x45 hi=0xCF)
frame = 01 03 00 00 00 0C 45 CF
```

This matches `fae_toolkit.protocols.modbus.build_read_holding_registers(1, 0, 12)`
in the Python package byte-for-byte.

## Roadmap

- Expose `faecore` to Python via pybind11 so the GUI can call the C++ CRC/codec.
