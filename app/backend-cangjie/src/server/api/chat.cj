package mossAi.server.api

import stdx.encoding.json.*
import stdx.net.http.*
import std.collection.HashMap


protected func chat(httpContext: HttpContext): Unit {
    let responseData = HashMap<String, JsonValue>()
    responseData.add("name", JsonString("张三"))
    responseData.add("age", JsonInt(15))

    let jsonString = JsonObject(responseData).toString() // 将JsonObject转为字符串
    let jsonBytes = jsonString // 将字符串转为UTF-8字节数组

    httpContext.responseBuilder.header("Content-Type", "application/json").body(jsonBytes) // 传入字节数组
}
