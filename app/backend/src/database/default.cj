package mossAi.database

import std.time.*
import std.math.numeric.*
import std.database.sql.*
import mysql.cdbc.*

public func useSql(): Unit {
    var driver = DriverManager.getDriver("mysql").getOrThrow()
    var property1 = ("username", "root")
    var property2 = ("password", "123456")
    var property3 = ("database", "Test")
    var property4 = ("host", "192.168.110.129")
    var property5 = ("port", "13306")
    var dataSource = driver.open("mysql://192.168.110.129", [property1, property2, property3,property4,property5])
    var connection = dataSource.connect()
//    插入
    var statemnt_INsert = connection.prepareStatement("insert into simple values (?, ?, ?, ?, ?, ?, ?, ?)")
    statemnt_INsert.set(1, 100)
    statemnt_INsert.set(2, "MySQL")
    statemnt_INsert.setNull(3)
    statemnt_INsert.set(4, 123.456789)
    statemnt_INsert.set(5, Decimal.parse("1.234567"))
    statemnt_INsert.set(6, DateTime.now())
    statemnt_INsert.set(7, DateTime.now())
    statemnt_INsert.set(8, DateTime.now())
    var result_INsert = statemnt_INsert.update()

    println("effect row: ${result_INsert.rowCount} lastInsertId: ${result_INsert.lastInsertId}")


    // 查询
    var statemnt = connection.prepareStatement("select * from simple")
    var result = statemnt.query()
while (result.next()) {
        result.get<UInt64>(1) |> println
        result.getOrNull<String>(2) |> println
        result.getOrNull<Int32>(3) |> println
        result.getOrNull<Float64>(4) |> println
        result.getOrNull<Decimal>(5) |> println
        result.getOrNull<DateTime>(6) |> println
        result.getOrNull<DateTime>(7) |> println
        result.getOrNull<DateTime>(8) |> println
    }
    
}