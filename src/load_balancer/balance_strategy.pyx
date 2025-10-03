from enum import IntEnum

class BalancingStrategy(IntEnum):
    ROUND_ROBIN = 0
    WEIGHTED_ROUND_ROBIN = 1
    RANDOM = 2
    WEIGHTED_RANDOM = 3
    LEAST_CONNECTIONS = 4
