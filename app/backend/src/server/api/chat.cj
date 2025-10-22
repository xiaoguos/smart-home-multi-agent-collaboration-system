package mossAi.server.api

import stdx.encoding.json.*
import stdx.net.http.*
import std.collection.HashMap
import stdx.log.*

// Chat 请求数据结构
class ChatRequest {
    public var query: String
    public var contextId: String
    
    public init(query: String, contextId: String) {
        this.query = query
        this.contextId = contextId
    }
}

// 解析 JSON 请求体
func parseChatRequest(body: String): ?ChatRequest {
    try {
        let json = JsonValue.fromStr(body)
        if (let obj <- json) {
            if (let jsonObj <- obj as JsonObject) {
                let map = jsonObj.value
                let query = map.get("query")
                let contextId = map.get("context_id") ?? JsonString("default")
                
                if (let q <- query) {
                    if (let queryStr <- q as JsonString) {
                        let ctxStr = if (let ctx <- contextId as JsonString) {
                            ctx.value
                        } else {
                            "default"
                        }
                        return ChatRequest(queryStr.value, ctxStr)
                    }
                }
            }
        }
    } catch (e: Exception) {
        getLogger("ChatAPI").error("Failed to parse chat request: ${e.message}")
    }
    return None
}

// 生成随机 UUID (简化版)
func generateUUID(): String {
    let timestamp = toString(System.currentTimeMillis())
    let random = toString((timestamp.hashCode() % 100000).abs())
    return "msg-${timestamp}-${random}"
}

// 调用 Conductor Agent A2A API
func callConductorAgent(query: String, contextId: String): String {
    try {
        // 创建 A2A 协议消息
        let messageId = generateUUID()
        
        // 构建 parts 数组
        let partData = HashMap<String, JsonValue>()
        partData.add("kind", JsonString("text"))
        partData.add("text", JsonString(query))
        let parts = JsonArray([JsonObject(partData)])
        
        // 构建完整消息
        let messageData = HashMap<String, JsonValue>()
        messageData.add("context_id", JsonString(contextId))
        messageData.add("role", JsonString("user"))
        messageData.add("parts", parts)
        messageData.add("message_id", JsonString(messageId))
        
        let jsonBody = JsonObject(messageData).toString()
        
        getLogger("ChatAPI").info("Sending to Conductor Agent: ${jsonBody}")
        
        // 使用 HTTP 客户端调用 A2A 服务 (端口 12000)
        let client = HttpClientBuilder().build()
        let request = RequestBuilder()
            .url("http://localhost:12000/send_message")
            .method(HttpMethod.POST)
            .header("Content-Type", "application/json")
            .body(jsonBody)
            .build()
        
        let response = client.send(request)
        
        if (response.statusCode == 200) {
            // 解析 A2A 响应
            let responseBody = response.body.toString()
            getLogger("ChatAPI").info("Conductor Agent response: ${responseBody}")
            
            // 尝试从 A2A 响应中提取文本内容
            try {
                let json = JsonValue.fromStr(responseBody)
                if (let obj <- json) {
                    if (let jsonObj <- obj as JsonObject) {
                        let map = jsonObj.value
                        
                        // 尝试提取 artifact 中的文本
                        if (let artifacts <- map.get("artifacts")) {
                            if (let artifactsArray <- artifacts as JsonArray) {
                                if (artifactsArray.value.size > 0) {
                                    if (let firstArtifact <- artifactsArray.value[0] as JsonObject) {
                                        let artifactMap = firstArtifact.value
                                        if (let parts <- artifactMap.get("parts")) {
                                            if (let partsArray <- parts as JsonArray) {
                                                if (partsArray.value.size > 0) {
                                                    if (let firstPart <- partsArray.value[0] as JsonObject) {
                                                        let partMap = firstPart.value
                                                        if (let root <- partMap.get("root")) {
                                                            if (let rootObj <- root as JsonObject) {
                                                                let rootMap = rootObj.value
                                                                if (let text <- rootMap.get("text")) {
                                                                    if (let textStr <- text as JsonString) {
                                                                        // 返回格式化的响应
                                                                        let resultData = HashMap<String, JsonValue>()
                                                                        resultData.add("content", JsonString(textStr.value))
                                                                        resultData.add("is_task_complete", JsonBool(true))
                                                                        resultData.add("require_user_input", JsonBool(false))
                                                                        return JsonObject(resultData).toString()
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        // 如果没有 artifacts，尝试从 message 中提取
                        if (let message <- map.get("message")) {
                            if (let msgObj <- message as JsonObject) {
                                let msgMap = msgObj.value
                                if (let parts <- msgMap.get("parts")) {
                                    if (let partsArray <- parts as JsonArray) {
                                        if (partsArray.value.size > 0) {
                                            if (let firstPart <- partsArray.value[0] as JsonObject) {
                                                let partMap = firstPart.value
                                                if (let text <- partMap.get("text")) {
                                                    if (let textStr <- text as JsonString) {
                                                        let resultData = HashMap<String, JsonValue>()
                                                        resultData.add("content", JsonString(textStr.value))
                                                        resultData.add("is_task_complete", JsonBool(true))
                                                        resultData.add("require_user_input", JsonBool(false))
                                                        return JsonObject(resultData).toString()
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (parseError: Exception) {
                getLogger("ChatAPI").error("Failed to parse A2A response: ${parseError.message}")
            }
            
            // 如果无法解析，返回原始响应
            return responseBody
        } else {
            getLogger("ChatAPI").error("Conductor Agent returned error: ${response.statusCode}")
            let errorData = HashMap<String, JsonValue>()
            errorData.add("error", JsonString("Conductor Agent 返回错误"))
            errorData.add("status_code", JsonInt(response.statusCode.toInt64()))
            return JsonObject(errorData).toString()
        }
    } catch (e: Exception) {
        getLogger("ChatAPI").error("Failed to call Conductor Agent: ${e.message}")
        let errorData = HashMap<String, JsonValue>()
        errorData.add("error", JsonString("无法连接到 Conductor Agent"))
        errorData.add("message", JsonString(e.message))
        return JsonObject(errorData).toString()
    }
}

// Chat API 处理函数
protected func chat(httpContext: HttpContext): Unit {
    try {
        // 设置 CORS 头
        httpContext.responseBuilder
            .header("Access-Control-Allow-Origin", "*")
            .header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            .header("Access-Control-Allow-Headers", "Content-Type")
        
        // 处理 OPTIONS 预检请求
        if (httpContext.request.method == HttpMethod.OPTIONS) {
            httpContext.responseBuilder.status(200).body("")
            return
        }
        
        // 获取请求体
        let body = httpContext.request.body.toString()
        
        // 解析请求
        if (let chatReq <- parseChatRequest(body)) {
            getLogger("ChatAPI").info("Received chat request: ${chatReq.query}")
            
            // 调用 Conductor Agent
            let result = callConductorAgent(chatReq.query, chatReq.contextId)
            
            // 返回响应
            httpContext.responseBuilder
                .header("Content-Type", "application/json; charset=utf-8")
                .body(result)
        } else {
            // 请求解析失败
            let errorResponse = HashMap<String, JsonValue>()
            errorResponse.add("error", JsonString("无效的请求格式"))
            let errorJson = JsonObject(errorResponse).toString()
            
            httpContext.responseBuilder
                .status(400)
                .header("Content-Type", "application/json; charset=utf-8")
                .body(errorJson)
        }
    } catch (e: Exception) {
        getLogger("ChatAPI").error("Error in chat handler: ${e.message}")
        let errorResponse = HashMap<String, JsonValue>()
        errorResponse.add("error", JsonString("服务器内部错误"))
        errorResponse.add("message", JsonString(e.message))
        let errorJson = JsonObject(errorResponse).toString()
        
        httpContext.responseBuilder
            .status(500)
            .header("Content-Type", "application/json; charset=utf-8")
            .body(errorJson)
    }
}