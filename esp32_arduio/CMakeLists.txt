# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html
# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(Arduio_MCP)

# idf.py build 会重写 compile_commands.json；构建后执行:
#   cmake --build build --target compile_commands_clangd
add_custom_target(
    compile_commands_clangd
    COMMAND ${CMAKE_COMMAND} -E echo "Patch compile_commands + symlink to project root for clangd"
    COMMAND python3 "${CMAKE_SOURCE_DIR}/tools/patch_compile_commands.py"
            "${CMAKE_BINARY_DIR}/compile_commands.json"
    COMMAND ${CMAKE_COMMAND} -E remove -f "${CMAKE_SOURCE_DIR}/compile_commands.json"
    COMMAND ${CMAKE_COMMAND} -E create_symlink "${CMAKE_BINARY_DIR}/compile_commands.json"
            "${CMAKE_SOURCE_DIR}/compile_commands.json"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Merge main sources into compile_commands.json"
    VERBATIM
)