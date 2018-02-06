#include "sequence.hpp"
#include <string>
#include <iostream>

using namespace std;

void sequence::set(string i, unsigned long int l, double c)
{
    read_id = i;
    read_len = l;
    cov = c;
}

void sequence::updateCov( double c )
{
    cov += c;
}
