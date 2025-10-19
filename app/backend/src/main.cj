package mossAi

import stdx.net.http.*
import std.time.*
import std.sync.*
import stdx.log.*
import stdx.encoding.json.*
import std.collection.HashMap

import mossAi.api.*

let server = ServerBuilder()
    .addr("127.0.0.1")
    .port(2100)
    .build()

    func startServer(): Unit {
    server.distributor.register("/hello",hello)
    
    server.logger.level = LogLevel.ALL
    server.serve()
}

main() {
    startServer()
}