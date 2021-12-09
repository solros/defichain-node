#ifndef DEFI_RPC_STATS_H
#define DEFI_RPC_STATS_H

#include <map>
#include <stdint.h>
#include <univalue.h>
#include <util/time.h>

/**
 * DeFi Blockchain RPC Stats class.
 */
class CRPCStats
{
private:
    std::map<std::string, UniValue> map;
public:
    void add(const std::string& name, const int64_t latency, const size_t payload);

    const UniValue get(const std::string& name) { return map[name]; };

    /**
    * Returns a full list of RPC stats
    * @returns full list of RPC stats.
    */
    std::map<std::string, UniValue> getList() { return map; };

    // void save();
};

extern CRPCStats statsRPC;

#endif // DEFI_RPC_STATS_H
