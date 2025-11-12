# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from toolkit.pre_load import neo_con
import os
import json

# =============================
# 预加载关系统计文件（relationStaticResult.txt）
# =============================
relationCountDict = {}
filePath = os.path.abspath(os.path.join(os.getcwd(), "."))
with open(filePath + "/toolkit/relationStaticResult.txt", "r", encoding="utf8") as fr:
    for line in fr:
        relationNameCount = line.split(",")
        relationName = relationNameCount[0][2:-1]
        relationCount = relationNameCount[1][1:-2]
        relationCountDict[relationName] = int(relationCount)


# =============================
# 工具函数：按关系出现次数排序
# =============================
def sortDict(relationDict):
    for i in range(len(relationDict)):
        relationName = relationDict[i]["rel"].get("type", "")
        relationCount = relationCountDict.get(relationName, 0)
        relationDict[i]["relationCount"] = relationCount
    relationDict = sorted(relationDict, key=lambda item: item["relationCount"], reverse=True)
    return relationDict


# =============================
# 实体关系搜索（单实体）
# =============================
def search_entity(request):
    ctx = {}
    if request.GET:
        entity = request.GET.get("user_text", "").strip()
        db = neo_con
        entityRelation = db.getEntityRelationbyEntity(entity)

        if len(entityRelation) == 0:
            ctx = {"title": "<h1>数据库中暂未添加该实体</h1>"}
            return render(request, "entity.html", {"ctx": json.dumps(ctx, ensure_ascii=False)})
        else:
            # 排序
            entityRelation = sortDict(entityRelation)
            return render(
                request, "entity.html", {"entityRelation": json.dumps(entityRelation, ensure_ascii=False)}
            )
    return render(request, "entity.html", {"ctx": ctx})


# =============================
# 关系搜索（双实体 + 关系）
# =============================
def search_relation(request):
    ctx = {}
    if request.GET:
        db = neo_con
        entity1 = request.GET.get("entity1_text", "").strip()
        relation = request.GET.get("relation_name_text", "").strip().lower()
        entity2 = request.GET.get("entity2_text", "").strip()
        searchResult = []

        # ------------------------
        # 仅输入 entity1 → 查询所有直接和间接相关关系
        # ------------------------
        if entity1 and not relation and not entity2:
            searchResult = db.findRelationByEntity(entity1)
            entity_TT_list = [record["n2"]["title"] for record in searchResult]

            # 递归拓展下一层关系
            for entity_TT in entity_TT_list:
                temp1 = db.findRelationByEntity2(entity_TT)
                temp2 = db.findRelationByEntity(entity_TT)
                searchResult += temp1 + temp2

            searchResult = sortDict(searchResult)

            if len(searchResult) > 0:
                # 确保 labels 可序列化
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # 仅输入 entity2 → 查询所有与之相连的关系
        # ------------------------
        if entity2 and not relation and not entity1:
            searchResult = db.findRelationByEntity2(entity2)
            searchResult = sortDict(searchResult)
            if len(searchResult) > 0:
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # entity1 + relation → 查找 entity1 通过该关系连接的节点
        # ------------------------
        if entity1 and relation and not entity2:
            searchResult = db.findOtherEntities(entity1, relation)
            searchResult = sortDict(searchResult)
            if len(searchResult) > 0:
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # entity2 + relation → 查找 entity2 的上游关系
        # ------------------------
        if entity2 and relation and not entity1:
            searchResult = db.findOtherEntities2(entity2, relation)
            searchResult = sortDict(searchResult)
            if len(searchResult) > 0:
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # entity1 + entity2 → 查找两实体之间的最短路径
        # ------------------------
        if entity1 and not relation and entity2:
            searchResult = db.findRelationByEntities(entity1, entity2)
            if len(searchResult) > 0:
                searchResult = sortDict(searchResult)
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # entity1 + relation + entity2 → 检查是否存在该关系
        # ------------------------
        if entity1 and entity2 and relation:
            searchResult = db.findEntityRelation(entity1, relation, entity2)
            if len(searchResult) > 0:
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # 全为空 → 返回所有关系
        # ------------------------
        if not entity1 and not relation and not entity2:
            searchResult = db.findAllRelation()
            if len(searchResult) > 0:
                searchResult = sortDict(searchResult)
                for r in searchResult:
                    r["n1"].setdefault("labels", [])
                    r["n2"].setdefault("labels", [])
                return render(
                    request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
                )

        # ------------------------
        # 无匹配结果
        # ------------------------
        ctx = {"title": "<h1>暂未找到相应的匹配</h1>"}
        return render(request, "relation.html", {"ctx": ctx})

    return render(request, "relation.html", {"ctx": ctx})


def search_full_reaction_path(request):
    ctx = {}
    if request.GET:
        db = neo_con
        reactant = request.GET.get("reactant_text", "").strip()

        if not reactant:
            ctx = {"title": "<h1>请输入反应物名称</h1>"}
            return render(request, "relation.html", {"ctx": ctx})

        searchResult = db.findFullReactionPath(reactant)

        if len(searchResult) > 0:
            # 确保所有节点都有 labels 字段
            for r in searchResult:
                r["n1"].setdefault("labels", [])
                r["n2"].setdefault("labels", [])
            searchResult = sortDict(searchResult)
            return render(
                request, "relation.html", {"searchResult": json.dumps(searchResult, ensure_ascii=False)}
            )

        ctx = {"title": "<h1>未找到该物质参与的反应路径</h1>"}
        return render(request, "relation.html", {"ctx": ctx})

    return render(request, "relation.html", {"ctx": ctx})
