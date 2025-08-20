# How to use this script

Process subset 1 (accounts 1-25)

    python aws-cspm-benchmark.py -n 4 -m 0

Process subset 2 (accounts 26-50)  

    python aws-cspm-benchmark.py -n 4 -m 1

Process subset 3 (accounts 51-75)

    python aws-cspm-benchmark.py -n 4 -m 2

Process subset 4 (accounts 76-100)

    python aws-cspm-benchmark.py -n 4 -m 3

With custom output prefix and other options

    python aws-cspm-benchmark.py -n 4 -m 0 -o my-aws-benchmark --threads 3 --batch-size 10
