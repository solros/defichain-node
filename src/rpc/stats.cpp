#include <rpc/stats.h>
#include <rpc/server.h>
#include <rpc/util.h>

void CRPCStats::add(const std::string& name, const int64_t latency, const size_t payload)
{
    UniValue info(UniValue::VOBJ);
    info.pushKV("timestamp", GetSystemTimeInSeconds());
    info.pushKV("latency", latency);
    info.pushKV("payload", (int64_t) payload);
    map[name].push_back(info);
}

UniValue StatsToJSON(const std::string name, std::vector<const UniValue> stats, bool verbose = false) {
    UniValue ret(UniValue::VOBJ);
    if (!stats.size()) return ret;

    int64_t min_latency = std::numeric_limits<int>::max(),
            min_payload = std::numeric_limits<int>::max(),
            avg_latency = 0,
            avg_payload = 0,
            max_latency = 0,
            max_payload = 0;
    UniValue history(UniValue::VARR);

    ret.pushKV("name", name);
    ret.pushKV("lastUsedTime", stats.back()["timestamp"]);
    for (const auto& data : stats)
    {
        int64_t latency = data["latency"].get_int();
        int64_t payload = data["payload"].get_int();

        if (latency < min_latency) min_latency = latency;
        if (latency > max_latency) max_latency = latency;
        if (payload < min_payload) min_payload = payload;
        if (payload > max_payload) max_payload = payload;
        avg_latency += latency;
        avg_payload += payload;

        if (verbose) history.push_back(data);
    }
    UniValue latencyObj(UniValue::VOBJ);
    latencyObj.pushKV("max", max_latency);
    latencyObj.pushKV("min", min_latency);
    latencyObj.pushKV("avg", (int64_t) avg_latency / stats.size());
    ret.pushKV("latency", latencyObj);

    UniValue payloadObj(UniValue::VOBJ);
    payloadObj.pushKV("max", max_payload);
    payloadObj.pushKV("min", min_payload);
    payloadObj.pushKV("avg", (int64_t) avg_payload / stats.size());
    ret.pushKV("payload", payloadObj);

    ret.pushKV("lastUsedTime", stats.back()["timestamp"]);
    ret.pushKV("count", (int64_t) stats.size());

    if (verbose) ret.pushKV("history", history);

    return ret;
}

static UniValue getrpcstats(const JSONRPCRequest& request)
{
    RPCHelpMan{"getrpcstats",
        "\nList used RPC commands for this session.\n",
        {
            {"command", RPCArg::Type::STR, RPCArg::Optional::NO, "The command to get stats for."},
            {"verbose", RPCArg::Type::BOOL, RPCArg::Optional::OMITTED, "If set, send full history for this command."}
        },
        RPCResults{},
        RPCExamples{
            HelpExampleCli("getrpcstats", "getblockcount") +
            HelpExampleRpc("getrpcstats", "getblockcount")
        },
    }.Check(request);

    bool verbose = false;
    if (!request.params[1].isNull()) verbose = request.params[1].get_bool();

    auto command = request.params[0].get_str();
    auto stats = statsRPC.get(command);

    return StatsToJSON(command, stats, verbose);
}

static UniValue listrpcstats(const JSONRPCRequest& request)
{
    RPCHelpMan{"listrpcstats",
        "\nList used RPC commands for this session.\n",
        {
            {"verbose", RPCArg::Type::BOOL, RPCArg::Optional::OMITTED, "If set, send full history for each command."}
        },
        RPCResults{},
        RPCExamples{
            HelpExampleCli("listrpcstats", "") +
            HelpExampleRpc("listrpcstats", "")
        },
    }.Check(request);

    bool verbose = false;
    if (!request.params[0].isNull()) verbose = request.params[0].get_bool();

    UniValue ret(UniValue::VARR);
    for (const auto& data : statsRPC.getList())
    {
        ret.push_back(StatsToJSON(data.first, data.second, verbose));
    }
    return ret;
}

// clang-format off
static const CRPCCommand commands[] =
{ //  category              name                      actor (function)         argNames
  //  --------------------- ------------------------  -----------------------  ----------
    { "stats",            "getrpcstats",              &getrpcstats,          {"command", "verbose"} },
    { "stats",            "listrpcstats",             &listrpcstats,         {"verbose"} },
};
// clang-format on

void RegisterStatsRPCCommands(CRPCTable &t)
{
    for (unsigned int vcidx = 0; vcidx < ARRAYLEN(commands); vcidx++)
        t.appendCommand(commands[vcidx].name, &commands[vcidx]);
}
