import rconbf3

connection = rconbf3.connect("10.0.0.22", 47200)
rconbf3.start_update(connection)

result = rconbf3.authenticate(connection, "w1ms4ndr4")
if result and result == ["OK"]:
    print(rconbf3.invoke(connection, "serverInfo"))
