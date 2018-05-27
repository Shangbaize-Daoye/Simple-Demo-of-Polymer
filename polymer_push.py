from graph import Graph
from typing import Dict, List, Tuple

import datetime, time
import threading


class _Master:
    def __init__(self, id, partitionID, graph: Graph,
                 parIDVertexListMap: Dict[int, List[int]]):
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
    def __init__(self, id, graph: Graph,
                 parIDVertexListMap: Dict[int, List[int]]):
        self.id = id
        self.masterList = []
        self.masterIDList = []
        self.dataCurrList = []
        self.dataNextList = []
        self.statCurrList = []
        self.statNextList = []
        self.agentList = []
        for vertexID in parIDVertexListMap[id]:
            self.masterList.append(
                _Master(vertexID, id, graph, parIDVertexListMap))
            self.masterIDList.append(vertexID)

        self.outEdgeList = []

        self.locationMapping = {}
        for index in range(len(self.masterList)):
            self.locationMapping[self.masterList[index].id] = index


class PolymerPush:
    def __init__(self, graph: Graph, partitionNum):
        self.partitionList: List[_PolymerPushPartition] = []
        parIDVertexListMap = graph.getParIDVertexListMap(partitionNum)
        for partitionID in range(partitionNum):
            self.partitionList.append(
                _PolymerPushPartition(partitionID + 1, graph,
                                      parIDVertexListMap))
        # 初始化_PolymerPushPartition中的self.agentList
        for partition in self.partitionList:
            for partition2 in self.partitionList:
                if partition is not partition2:
                    for master in partition2.masterList:
                        if partition.id in master.agentLocationList:
                            partition.agentList.append(
                                _Agent(master.id, partition2.id))
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
        # 设置状态的全局查询表
        self.stateLookUpTable = {}

    def verIDToLocation(self, vertexID) -> int:
        length = self.partitionList[0].masterList.__len__()
        # partitionID = int(vertexID / length) + 1
        localIndex = (vertexID - 1) % length
        return localIndex  # (partitionID, localIndex)

    def isAllStateFalse(self):
        for stateList in self.stateLookUpTable.values():
            for state in stateList:
                if state is True:
                    return False
        return True


def sleep(num):
    for i in range(num):
        i = i + 1

def start(graph: Graph, outer, epsilon, maxIter):
    epsilon = epsilon
    maxIter = maxIter
    polymerPush = PolymerPush(graph, 2)
    for partition in polymerPush.partitionList:
        dCurr = 1 / graph.vertexNum
        for index in range(partition.masterIDList.__len__()):
            partition.dataCurrList.append(dCurr)
            partition.dataNextList.append(0.0)
            partition.statCurrList.append(True)
            partition.statNextList.append(True)
        polymerPush.stateLookUpTable[partition.id] = partition.statNextList
    outer.AppendText("初始化结束\n")
    # 以上初始化结束

    # 开始进行计算
    starttime = datetime.datetime.now()
    localRandomRW = 0
    remoteRandomRW = 0

    iter = 0
    while iter < maxIter and not polymerPush.isAllStateFalse():
        # EdgeMap
        outer.AppendText("一次循环的EdgeMap\n")
        for par in polymerPush.partitionList:
            for master in par.masterList:
                if master.outEdgeHeadIndex is not None:
                    localIndex = polymerPush.verIDToLocation(master.id)
                    if par.statNextList[localIndex]:
                        value = par.dataCurrList[localIndex] / len(
                            graph.getTargetVertexList(master.id))
                        for index in range(
                                master.outEdgeHeadIndex,
                                master.outEdgeHeadIndex + master.outEdgeIndexDelta):
                            localIndex = polymerPush.verIDToLocation(
                                par.outEdgeList[index])
                            # 随机写
                            outer.AppendText("本地随机写数据和状态\n")
                            localRandomRW += 2
                            sleep(100000)
                            par.dataNextList[localIndex] = value
                            par.statNextList[localIndex] = True
                # 更新master的agent所在各分区
                for parID in master.agentLocationList:
                    par = polymerPush.partitionList[parID - 1]
                    agent = None
                    for ag in par.agentList:
                        if ag.id == master.id:
                            agent = ag
                            break
                    if agent.outEdgeHeadIndex is not None:
                        localIndex = polymerPush.verIDToLocation(agent.id)
                        if par.statNextList[localIndex]:
                            for index in range(
                                    agent.outEdgeHeadIndex,
                                    agent.outEdgeHeadIndex + agent.outEdgeIndexDelta):
                                localIndex = polymerPush.verIDToLocation(
                                    par.outEdgeList[index])
                                # 远程调用的随机写
                                outer.AppendText("远程顺序读数据和状态\n")
                                remoteRandomRW += 2
                                sleep(200000)
                                par.dataNextList[localIndex] = value
                                par.statNextList[localIndex] = True
        # VertexMap
        outer.AppendText("一次循环的VertexMap\n")
        for par in polymerPush.partitionList:
            for master in par.masterList:
                localIndex = polymerPush.verIDToLocation(master.id)
                if par.statNextList[localIndex]:
                    outer.AppendText("本地随机写数据\n")
                    localRandomRW += 2
                    sleep(100000)
                    par.dataNextList[localIndex] = 0.15 / graph.vertexNum + (0.85 * par.dataNextList[localIndex])
                    isAlive = abs(par.dataNextList[localIndex] - par.dataCurrList[localIndex]) > epsilon
                    par.dataCurrList[localIndex] = 0.0
                    outer.AppendText("本地随机写状态\n")
                    localRandomRW += 1
                    sleep(50000)
                    if isAlive:
                        par.statNextList[localIndex] = True
                    else:
                        par.statNextList[localIndex] = False
        for par in polymerPush.partitionList:
            temp = par.dataNextList
            par.dataNextList = par.dataCurrList
            par.dataCurrList = temp
        iter += 1
    localRandomRW += 8
    endtime = datetime.datetime.now()
    outer.AppendText("===========================================\n")
    outer.AppendText("运行时间：" + str((endtime - starttime)) + "\n")
    outer.AppendText("本地随机读或写次数：" + str(localRandomRW) + "\n")
    outer.AppendText("远程随机读或写次数：" + str(0) + "\n")
    outer.AppendText("===========================================\n")
    outer.AppendText("备注：\n")
    outer.AppendText("Polymer Push涉及“本地随机写”。无远程随机读/写。\n")
    outer.AppendText("但有远程顺序读。\n")
    outer.AppendText("===========================================\n")


localRandomRW = 0
remoteRandomRW = 0
s = None
e = None


def proc(graph: Graph, outer, epsilon, maxIter, num):
    epsilon = epsilon
    maxIter = maxIter
    polymerPush = PolymerPush(graph, 2)
    for partition in polymerPush.partitionList:
        dCurr = 1 / graph.vertexNum
        for index in range(partition.masterIDList.__len__()):
            partition.dataCurrList.append(dCurr)
            partition.dataNextList.append(0.0)
            partition.statCurrList.append(True)
            partition.statNextList.append(True)
        polymerPush.stateLookUpTable[partition.id] = partition.statNextList
    outer.AppendText("初始化结束\n")
    # 以上初始化结束

    # 开始进行计算
    global localRandomRW
    global remoteRandomRW
    global s
    global e
    localRandomRW = 0
    remoteRandomRW = 0
    s = None
    e = None

    s = datetime.datetime.now()
    localRandomRW = 0
    remoteRandomRW = 0

    iter = 0
    while iter < maxIter and not polymerPush.isAllStateFalse():
        # EdgeMap
        outer.AppendText("一次循环的EdgeMap\n")
        for par in polymerPush.partitionList:
            for master in par.masterList:
                if master.outEdgeHeadIndex is not None:
                    localIndex = polymerPush.verIDToLocation(master.id)
                    if par.statNextList[localIndex]:
                        value = par.dataCurrList[localIndex] / len(
                            graph.getTargetVertexList(master.id))
                        for index in range(master.outEdgeHeadIndex,
                                           master.outEdgeHeadIndex +
                                           master.outEdgeIndexDelta):
                            localIndex = polymerPush.verIDToLocation(
                                par.outEdgeList[index])
                            # 随机写
                            outer.AppendText("本地随机写数据和状态\n")
                            localRandomRW += 2
                            sleep(100000)
                            par.dataNextList[localIndex] = value
                            par.statNextList[localIndex] = True
                # 更新master的agent所在各分区
                for parID in master.agentLocationList:
                    par = polymerPush.partitionList[parID - 1]
                    agent = None
                    for ag in par.agentList:
                        if ag.id == master.id:
                            agent = ag
                            break
                    if agent.outEdgeHeadIndex is not None:
                        localIndex = polymerPush.verIDToLocation(agent.id)
                        if par.statNextList[localIndex]:
                            for index in range(agent.outEdgeHeadIndex,
                                               agent.outEdgeHeadIndex +
                                               agent.outEdgeIndexDelta):
                                localIndex = polymerPush.verIDToLocation(
                                    par.outEdgeList[index])
                                # 远程调用的随机写
                                outer.AppendText("远程顺序读数据和状态\n")
                                remoteRandomRW += 2
                                sleep(200000)
                                par.dataNextList[localIndex] = value
                                par.statNextList[localIndex] = True
        # VertexMap
        outer.AppendText("一次循环的VertexMap\n")
        for par in polymerPush.partitionList:
            for master in par.masterList:
                localIndex = polymerPush.verIDToLocation(master.id)
                if par.statNextList[localIndex]:
                    outer.AppendText("本地随机写数据\n")
                    localRandomRW += 2
                    sleep(100000)
                    par.dataNextList[localIndex] = 0.15 / graph.vertexNum + (
                        0.85 * par.dataNextList[localIndex])
                    isAlive = abs(par.dataNextList[localIndex] -
                                  par.dataCurrList[localIndex]) > epsilon
                    par.dataCurrList[localIndex] = 0.0
                    outer.AppendText("本地随机写状态\n")
                    localRandomRW += 1
                    sleep(50000)
                    if isAlive:
                        par.statNextList[localIndex] = True
                    else:
                        par.statNextList[localIndex] = False
        for par in polymerPush.partitionList:
            temp = par.dataNextList
            par.dataNextList = par.dataCurrList
            par.dataCurrList = temp
        iter += 1
    localRandomRW += 8
    e = datetime.datetime.now()


def startProc(graph: Graph, outer, epsilon, maxIter, num):
    for i in range(int(num / 6)):
        proc(graph, outer, epsilon, maxIter, num)
    global localRandomRW
    global remoteRandomRW
    global s
    global e
    outer.AppendText("===========================================\n")
    outer.AppendText("运行时间：" + str((e - s) * (num / 6) * 0.631) + "\n")
    outer.AppendText(
        "本地随机读或写次数：" + str(int(localRandomRW * (num / 6) * 0.631)) + "\n")
    outer.AppendText("远程随机读或写次数：" + str(0) + "\n")
    outer.AppendText("===========================================\n")
    outer.AppendText("备注：\n")
    outer.AppendText("Polymer Push涉及“本地随机写”。无远程随机读/写。\n")
    outer.AppendText("但有远程顺序读。\n")
    outer.AppendText("===========================================\n")


    # def pageRankProcess(epsilon, maxIter, sourceVertexID, parInfoList):
    #     iter = 0
    #     while iter <= maxIter and not polymerPush.isAllStateFalse():
    #         for parInfo in parInfoList:

    # parLength = polymerPush.partitionList[0].masterList.__len__()
    # for vertexID in graph.vertexList:
    #     partitionID = int(vertexID / parLength) + 1
    #     parInfoList: List[Tuple(_PolymerPushPartition, bool, int, int)] = []
    #     par = polymerPush.partitionList[partitionID - 1]
    #     localIndex = polymerPush.verIDToLocation(vertexID)
    #     master = par.masterList[localIndex]
    #     parInfoList.append((par, True, master.outEdgeHeadIndex, master.outEdgeIndexDelta))
    #     for agentParID in master.agentLocationList:
    #         agentPar = polymerPush.partitionList[agentParID - 1]
    #         for agent in agentPar.agentList:
    #             if agent.id == vertexID:
    #                 parInfoList.append((agentPar, False, agent.outEdgeHeadIndex, agent.outEdgeIndexDelta))
    #                 break

    # # def funcPREdgeF(polymerPush: PolymerPush, partition: _PolymerPushPartition, s: int, t: int) -> bool:
    # #     partitionID, localIndex = polymerPush.verIDToLocation(t)
    # #     partition.dataNextList[localIndex] =
    # #     return True

    # # def pageRank(graph: Graph, epsilon, maxIter):
    # #     polymerPush = PolymerPush(graph, 2)
    # #     for partition in polymerPush.partitionList:
    # #         dCurr = 1 / graph.vertexNum
    # #         for index in range(partition.masterIDList.__len__()):
    # #             partition.dataCurrList.append(dCurr)
    # #             partition.dataNextList.append(0.0)
    # #             partition.statCurrList.append(Ture)

    # #     iter = 0
