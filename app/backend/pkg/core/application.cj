package core

import stdx.net.http.*
import std.time.*
import std.sync.*
import stdx.log.*


let server = ServerBuilder()
    .addr("127.0.0.1")
    .port(210)
    .build()

func startServer(): Unit {
    // 2. 注册请求处理逻辑
    server.distributor.register("/hello", {httpContext =>
        httpContext.responseBuilder.body("Hello Cangjie!")
    })
    server.serve()
}

main(): Int64 {
    startServer()
    return 0
}