from graph import Graph
from typing import Dict, List, Tuple


class _Master:
    def __init__(self, id, partitionID, graph: Graph, parIDVertexListMap: Dict[int, List[int]]):
        self.id = id
        self.agentLocationList = []
        self.outEdgeHeadIndex: int
        self.outEdgeIndexDelta: int
        targetVertexList = graph.getTargetVertexList(id)
        for parID, lst in parIDVertexListMap.items():
            if parID == partitionID:
                continue
            else:
                for targetVertex in targetVertexList:
                    if targetVertex in lst:
                        self.agentLocationList.append(parID)
                        break


class _Agent:
    def __init__(self, vertexID, masterLocation: int):
        self.id = vertexID
        self.masterLocation = masterLocation
        self.outEdgeHeadIndex: int
        self.outEdgeIndexDelta: int


class _PolymerPushPartition:
    def __init__(self, id, graph: Graph, parIDVertexListMap: Dict[int, List[int]]):
        self.id = id
        self.masterList = []
        self.masterIDList = []
        self.dataCurrList = []
        self.dataNextList = []
        self.statCurrList = []
        self.statNextList = []
        self.agentList = []
        for vertexID in parIDVertexListMap[id]:
            self.masterList.append(_Master(vertexID, id, graph, parIDVertexListMap))
            self.masterIDList.append(vertexID)

        self.outEdgeList = []

        self.locationMapping = {}
        for index in range(len(self.masterList)):
            self.locationMapping[self.masterList[index].id] = index


class PolymerPush:
    def __init__(self, partitionNum):
        self.partitionList: List[_PolymerPushPartition] = []
        graph = Graph()
        parIDVertexListMap = graph.getParIDVertexListMap(partitionNum)
        for partitionID in range(partitionNum):
            self.partitionList.append(_PolymerPushPartition(partitionID + 1, graph, parIDVertexListMap))
        # 初始化_PolymerPushPartition中的self.agentList
        for partition in self.partitionList:
            for partition2 in self.partitionList:
                if partition is not partition2:
                    for master in partition2.masterList:
                        if partition.id in master.agentLocationList:
                            partition.agentList.append(_Agent(master.id, partition2.id))
        # 初始化_PolymerPushPartition中的self.outEdgeList
        for partition in self.partitionList:
            headIndex = 0
            for master in partition.masterList:
                cursor = 0
                for targetVertex in graph.getTargetVertexList(master.id):
                    if targetVertex in partition.masterIDList:
                        partition.outEdgeList.append(targetVertex)
                        cursor += 1
                if cursor == 0:
                    master.outEdgeHeadIndex = None
                    master.outEdgeIndexDelta = None
                else:
                    master.outEdgeHeadIndex = headIndex
                    master.outEdgeIndexDelta = cursor
                    headIndex += cursor
            for agent in partition.agentList:
                cursor = 0
                for targetVertex in graph.getTargetVertexList(agent.id):
                    if targetVertex in partition.masterIDList:
                        partition.outEdgeList.append(targetVertex)
                        cursor += 1
                if cursor == 0:
                    agent.outEdgeHeadIndex = None
                    agent.outEdgeIndexDelta = None
                else:
                    agent.outEdgeHeadIndex = headIndex
                    agent.outEdgeIndexDelta = cursor
                    headIndex += cursor

    def verIDToLocation(self, vertexID) -> Tuple[int, int]:
        length = self.partitionList[0].masterList.__len__()
        partitionID = int(vertexID / length) + 1
        localIndex = (vertexID - 1) % length
        return (partitionID, localIndex)


if __name__ == "__main__":
    polymerPush = PolymerPush(2)
    for partition in polymerPush.partitionList:
        print(partition.outEdgeList)
        # print(index.id)
        for master in partition.masterList:
            print(master.outEdgeHeadIndex)
        for agent in partition.agentList:
            print(agent.outEdgeHeadIndex)
