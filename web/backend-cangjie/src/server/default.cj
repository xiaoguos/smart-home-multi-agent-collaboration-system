package mossAi.server

import stdx.net.http.*
import std.time.*
import std.sync.*
import stdx.log.*
import stdx.encoding.json.*
import std.collection.HashMap
import mossAi.server.api.*

let server = ServerBuilder().addr("127.0.0.1").port(2100).build()

public func startServer(): Unit {
    server.distributor.register("/hello", hello)
    server.distributor.register("/api/chat", chat)

    server.logger.level = LogLevel.ALL

    server.serve()
}
