#include <libain.hpp>
#include <rpc/libain_wrapper.hpp>

void fill_block(Block& block)
{
    block.hash = std::string("foobar");
}
