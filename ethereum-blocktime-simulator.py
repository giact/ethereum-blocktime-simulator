import time
import random
import math

HOMESTEAD_BLOCK = 1150000
HOMESTEAD_TIMESTAMP = 1457981393


BEGIN_BLOCK = 1662067  # https://live.ether.camp/block/1662067
BEGIN_TIMESTAMP = 1465327846

LAST_BLOCK = 1762067  # https://live.ether.camp/block/1762067
LAST_TIMESTAMP = 1466761852
LAST_DIFFICULTY = 52111077886421

AVERAGE_BLOCKTIME = float(LAST_TIMESTAMP - BEGIN_TIMESTAMP) / (LAST_BLOCK - BEGIN_BLOCK)  # Currently: 14.34006


# 2016-03: 14.453T
# 2016-04: 23.749T (+9.296T)
# 2016-05: 34.484T (+10.753T)
# 2016-06: 42.000T (+7.516T)
# Average increase: 9.18T per month

MINING_POWER_INCREASE_PER_MONTH = 9.180 * 1000000000000

# MINING_POWER_INCREASE_PER_MONTH = 0  # use this if you do not want to simulate any increase in mining power


class Block:
    def __init__(self, number, timestamp, parent):
        self.number = number
        self.timestamp = timestamp
        if isinstance(parent, Block):  # if parent is a block, let's compute the difficulty
            self.difficulty = self.compute_difficulty(parent)
        else:  # otherwise, assume parent is actually the difficulty (for our first block)
            self.difficulty = int(parent)

    def bomb(self):
        return 2 ** ((self.number / 100000) - 2)  # the "difficulty bomb"

    def compute_difficulty(self, parent):
        d0 = 131072  # difficulty floor as defined by the protocol
        x = parent.difficulty / 2048
        if self.timestamp <= parent.timestamp:  # protocol demands a strictly increasing timestamp
            raise ValueError(
                "Timestamp must always increase (parent: %d; self: %d)" % (parent.timestamp, self.timestamp)
            )
        if self.number < HOMESTEAD_BLOCK:
            # older protocol
            if self.timestamp < parent.timestamp + 13:
                sigma = 1
            else:
                sigma = -1
        else:
            # current protocol
            sigma = max(1 - (self.timestamp - parent.timestamp) / 10, -99)
        epsilon = self.bomb()
        return max(d0, parent.difficulty + sigma * x + epsilon)

    def next_block(self, timestamp):
        return Block(self.number + 1, timestamp, self)

    def __str__(self):
        return "Block #%d; Timestamp = %d : Difficulty = %d" % (self.number, self.timestamp, self.difficulty)


class MiningNetwork:
    def __init__(self, timestamp, difficulty):
        self.timestamp = timestamp  # At this point in time...
        # ... the network was able to mine blocks with an average time of [AVERAGE_BLOCKTIME]...
        self.difficulty = difficulty  # ... with this difficulty

    def mining_power(self, timestamp):
        # return the mining power of the network at timestamp
        # measured in the difficulty needed to have a block every [AVERAGE_BLOCKTIME] seconds
        # using a simple linear increase over time
        return self.difficulty + int(MINING_POWER_INCREASE_PER_MONTH * (timestamp - self.timestamp) / (3600 * 24 * 30))

    def mine(self, timestamp, difficulty):
        # simulates the network mining a new block using the exponential distribution
        # https://en.wikipedia.org/wiki/Exponential_distribution
        # returns the seconds elapsed
        #
        # rate parameter (lambda): blocks found per second
        rate = float(self.mining_power(timestamp)) / difficulty / AVERAGE_BLOCKTIME
        # roll a random probability between 0 and 1
        probability = random.random()
        # use the quantile (inverse) function to figure out the elapsed time from the given probability:
        elapsed_time = -math.log(1 - probability) / rate
        # we have to return an int > 0
        return int(math.ceil(elapsed_time))  # this gives me an average time of 14.19s


def unit(number):
    output = str(number)
    prefixes = ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    for prefix in prefixes:
        if number < 1000:
            break
        else:
            output = "%.2f%s" % (float(number) / 1000, prefix)
            number /= 1000
    return output


def run_block_test():
    # Test cases based on real blocks
    # Difficulty increasing
    assert Block(1752260, 1466621516, 51684547161764).next_block(1466621521).difficulty == 51709783789825
    # Difficulty decreasing
    assert Block(1752334, 1466622338, 52318863219327).next_block(1466622382).difficulty == 52242224292302
    # Block number = k*100000 - 2
    test = Block(1699998, 1465869436, 50227882576836)
    # Block number = k*100000 - 1
    test = test.next_block(1465869441)
    assert test.difficulty == 50252407926509
    # Block number = k*100000
    test = test.next_block(1465869449)
    assert test.difficulty == 50276945267834
    # Block number = k*100000 + 1
    test = test.next_block(1465869471)
    assert test.difficulty == 50252396010921


def run_mining_network_test(seconds, samples):
    timestamp = int(time.time())  # doesn't really matter
    total_time = 0
    for i in xrange(0, samples):
        difficulty = random.randint(10000000000000, 100000000000000)
        test = MiningNetwork(timestamp, difficulty)
        total_time += test.mine(time.time(), difficulty * seconds / 15)
    average = float(total_time) / samples
    assert abs(average - seconds) <= 1.5  # tolerate some error? (we're using integers after all)


def run_test():
    run_block_test()
    for i in xrange(0, 100):
        run_mining_network_test(random.randint(10, 20), 10000)

# run_test()

start_block = Block(LAST_BLOCK, LAST_TIMESTAMP, LAST_DIFFICULTY)
network = MiningNetwork(start_block.timestamp, start_block.difficulty)
block = start_block
total_blocktime = 0
count = 0
for i in xrange(start_block.number, 5500000):
    parent_block = block
    blocktime = network.mine(block.timestamp, block.difficulty)
    block = block.next_block(block.timestamp + blocktime)
    total_blocktime += blocktime
    count += 1
    if (block.number % 50000) == 0:
        print block.number,\
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block.timestamp)),\
            "| mining power:", unit(network.mining_power(block.timestamp)),\
            "| block difficulty:", unit(block.difficulty),\
            "| average blocktime:", "%.2fs" % (float(total_blocktime) / count),\
            "| bomb:", unit(block.bomb())
        total_blocktime = 0
        count = 0
