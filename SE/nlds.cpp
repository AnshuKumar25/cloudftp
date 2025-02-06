#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdlib>
#include <queue>
#include <set>

    using namespace std;

#define SIZE 20
#define PROB 2.0
#define INT_MAX 100000



vector<vector<int>> map(SIZE, vector<int>(SIZE, 0));
vector<int> dist_map(SIZE, INT_MAX);

void dijkstra(int start)
{
    queue<int> q;
    set<int> visited;
    q.push(start);
    dist_map[start] = 0;
    int x;
    while (q.size() != 0)
    {
        x = q.front();
        q.pop();
        for (int i = 0; i < SIZE; i++)
        {
            if (map[x][i] != 0)
            {
                dist_map[i] = min(dist_map[x] + map[x][i], dist_map[i]);
                if (visited.find(i) == visited.end())
                {
                    q.push(i);
                    visited.insert(i);
                }
            }
        }
    }
}

void make_city()
{
    int dist, prob, n, bias = 0;
    for (int i = 0; i < SIZE; i++)
    {
        for (int j = 0; j < SIZE; j++)
        {
            n = 0;
            prob = rand() % 100;
            if (j == SIZE - 1 && n == 0)
                bias = 100;
            if (map[i][j] == 0 && i != j && prob <= PROB + bias)
            {
                dist = rand() % 50;
                map[i][j] = dist;
                map[j][i] = dist;
                n++;
                bias = 0;
                if (n > 3)
                {
                    break;
                }
            }
            else
            {
                bias += 0.5;
            }
        }
    }
}

void print()
{
    for (int i = 0; i < SIZE; i++)
    {
        for (int j = 0; j < SIZE; j++)
        {
            cout << map[i][j] << " ";
        }
        cout << endl;
    }
}

int main()
{
    make_city();
    // print();
    dijkstra(0);
    cout << endl;
    // for(auto x:dist_map) cout << x << " ";
    return 0;
}
