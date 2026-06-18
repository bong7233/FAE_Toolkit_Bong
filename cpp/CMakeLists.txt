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

# Optional: build the pybind11 Python module (`faecore`). Enabled in CI with
#   cmake -S cpp -B build -DFAE_BUILD_PYBIND=ON -Dpybind11_DIR=$(python -m pybind11 --cmakedir)
option(FAE_BUILD_PYBIND "Build the pybind11 Python module" OFF)
if(FAE_BUILD_PYBIND)
  find_package(pybind11 CONFIG REQUIRED)
  pybind11_add_module(faecore_py python/bindings.cpp src/crc.cpp src/modbus.cpp)
  target_include_directories(faecore_py PRIVATE include)
  set_target_properties(faecore_py PROPERTIES OUTPUT_NAME faecore)
  # Emit the module into build/py/ on every generator/config for easy import.
  foreach(cfg "" _DEBUG _RELEASE _RELWITHDEBINFO _MINSIZEREL)
    set_target_properties(faecore_py PROPERTIES
      LIBRARY_OUTPUT_DIRECTORY${cfg} ${CMAKE_BINARY_DIR}/py
      RUNTIME_OUTPUT_DIRECTORY${cfg} ${CMAKE_BINARY_DIR}/py)
  endforeach()
endif()
