cmake_minimum_required(VERSION 3.16)
project(fae_toolkit_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MSVC)
  add_compile_options(/W4 /permissive-)
else()
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Shared protocol core (CRC + Modbus framing), the C++ counterpart of the
# Python fae_toolkit.core / fae_toolkit.protocols modules.
add_library(faecore src/crc.cpp src/modbus.cpp)
target_include_directories(faecore PUBLIC include)

# Field utility: compute a Modbus CRC for a sequence of bytes.
add_executable(fae_crc src/main.cpp)
target_link_libraries(fae_crc PRIVATE faecore)

enable_testing()
add_executable(crc_tests tests/test_crc.cpp)
target_link_libraries(crc_tests PRIVATE faecore)
add_test(NAME crc_tests COMMAND crc_tests)
