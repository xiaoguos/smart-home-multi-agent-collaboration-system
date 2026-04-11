# 从项目根目录 .env 读取 WIFI_SSID / WIFI_PASSWORD，生成 wifi_credentials.h（优先于 menuconfig）
set(_dotenv "${CMAKE_SOURCE_DIR}/../.env")
set(MCP_WIFI_SSID_RAW "")
set(MCP_WIFI_PASS_RAW "")

if(EXISTS "${_dotenv}")
    file(STRINGS "${_dotenv}" _dotenv_lines ENCODING UTF-8)
    foreach(_line IN LISTS _dotenv_lines)
        string(REGEX REPLACE "^[ \t]*#.*" "" _line "${_line}")
        string(LENGTH "${_line}" _llen)
        if(_llen EQUAL 0)
            continue()
        endif()
        if(_line MATCHES "^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(.*)$")
            set(_k "${CMAKE_MATCH_1}")
            set(_v "${CMAKE_MATCH_2}")
            string(REGEX REPLACE "[ \t]*#.*$" "" _v "${_v}")
            string(STRIP "${_v}" _v)
            if(_v MATCHES "^\"(.*)\"$")
                set(_v "${CMAKE_MATCH_1}")
            elseif(_v MATCHES "^'(.*)'$")
                set(_v "${CMAKE_MATCH_1}")
            endif()
            if(_k STREQUAL "WIFI_SSID")
                set(MCP_WIFI_SSID_RAW "${_v}")
            elseif(_k STREQUAL "WIFI_PASSWORD")
                set(MCP_WIFI_PASS_RAW "${_v}")
            endif()
        endif()
    endforeach()
endif()

function(mcp_c_string_escape input outvar)
    string(REPLACE "\\" "\\\\" _s "${input}")
    string(REPLACE "\"" "\\\"" _s "${_s}")
    string(REPLACE "\n" "\\n" _s "${_s}")
    string(REPLACE "\r" "\\r" _s "${_s}")
    set(${outvar} "${_s}" PARENT_SCOPE)
endfunction()

set(_wifi_hdr "${CMAKE_BINARY_DIR}/wifi_credentials.h")
if(NOT MCP_WIFI_SSID_RAW STREQUAL "")
    mcp_c_string_escape("${MCP_WIFI_SSID_RAW}" MCP_WIFI_SSID_C)
    mcp_c_string_escape("${MCP_WIFI_PASS_RAW}" MCP_WIFI_PASS_C)
    file(WRITE "${_wifi_hdr}"
        "#pragma once\n"
        "/* Generated from .env — do not edit */\n"
        "#define MCP_WIFI_SSID_VALUE \"${MCP_WIFI_SSID_C}\"\n"
        "#define MCP_WIFI_PASSWORD_VALUE \"${MCP_WIFI_PASS_C}\"\n"
        "#define MCP_WIFI_FROM_DOTENV 1\n"
    )
    message(STATUS "WiFi credentials: using project root .env (WIFI_SSID set)")
else()
    file(WRITE "${_wifi_hdr}"
        "#pragma once\n"
        "/* No WIFI_SSID in .env — use menuconfig MCP_WIFI_* (include sdkconfig.h before this header) */\n"
        "#define MCP_WIFI_SSID_VALUE CONFIG_MCP_WIFI_SSID\n"
        "#define MCP_WIFI_PASSWORD_VALUE CONFIG_MCP_WIFI_PASSWORD\n"
        "#define MCP_WIFI_FROM_DOTENV 0\n"
    )
    message(STATUS "WiFi credentials: using sdkconfig CONFIG_MCP_WIFI_* (set .env WIFI_SSID to override)")
endif()

idf_component_register(
    SRCS "main.c" "audio_mcp.c" "mcp_http.c"
    INCLUDE_DIRS "." "${CMAKE_BINARY_DIR}"
    PRIV_REQUIRES esp_driver_uart esp_driver_gpio esp_driver_i2s esp_http_server esp_wifi esp_netif
                  esp_event esp_ringbuf nvs_flash json mbedtls
)

# 供 clangd/部分 C 扩展在未能使用 compile_commands 条目时回退（路径随本机 IDF 生成，已加入 .gitignore）
if(DEFINED ENV{IDF_PATH})
    set(_idf "$ENV{IDF_PATH}")
    set(_cfg "${CMAKE_SOURCE_DIR}/../build/config")
    set(_mcf "${CMAKE_SOURCE_DIR}/compile_flags.txt")
    file(WRITE "${_mcf}" "")
    foreach(_line IN ITEMS
            "-xc"
            "-std=gnu23"
            "-I${_cfg}"
            "-I${CMAKE_SOURCE_DIR}"
            "-I${CMAKE_BINARY_DIR}"
            "-I${_idf}/components/esp_ringbuf/include"
            "-I${_idf}/components/mbedtls/mbedtls/include"
            "-I${_idf}/components/mbedtls/port/include"
            "-I${_idf}/components/json/cJSON"
            "-I${_idf}/components/esp_http_server/include"
            "-I${_idf}/components/esp_wifi/include"
            "-I${_idf}/components/esp_netif/include"
            "-I${_idf}/components/esp_event/include"
            "-I${_idf}/components/nvs_flash/include"
            "-I${_idf}/components/esp-tls"
            "-I${_idf}/components/esp-tls/esp-tls-crypto"
            "-I${_idf}/components/http_parser"
            "-I${_idf}/components/wpa_supplicant/include"
            "-I${_idf}/components/wpa_supplicant/esp_supplicant/include"
            "-I${_idf}/components/esp_coex/include"
            "-I${_idf}/components/lwip/include"
            "-I${_idf}/components/lwip/include/apps"
            "-I${_idf}/components/lwip/lwip/src/include"
            "-I${_idf}/components/lwip/port/include"
            "-I${_idf}/components/lwip/port/freertos/include"
            "-I${_idf}/components/lwip/port/esp32xx/include"
            "-DESP_PLATFORM"
    )
        file(APPEND "${_mcf}" "${_line}\n")
    endforeach()
endif()

# 为 clangd 补全 compile_commands.json（仅当已有 main.c 条目时复制出 audio_mcp.c / mcp_http.c）
set(_compile_commands "${CMAKE_SOURCE_DIR}/../build/compile_commands.json")
if(EXISTS "${_compile_commands}")
    find_program(MCP_PATCH_PY python3)
    if(MCP_PATCH_PY)
        execute_process(
            COMMAND "${MCP_PATCH_PY}" "${CMAKE_SOURCE_DIR}/../tools/patch_compile_commands.py"
                    "${_compile_commands}"
            RESULT_VARIABLE _pcc_rv
        )
    endif()
endif()
