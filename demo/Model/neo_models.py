from py2neo import Graph

class Neo4j():
    graph = None

    def __init__(self):
        print("create neo4j class ...")

    def connectDB(self):
        self.graph = Graph("bolt://localhost:7687", auth=("neo4j", "LzhLzj508"))

    # 通用方法：执行查询并附加 labels
    def _query_with_labels(self, cypher, **params):
        records = self.graph.run(cypher, **params)
        result = []
        for record in records:
            n1 = dict(record['n1'])
            n2 = dict(record['n2'])
            rel = dict(record['rel'])
            # 添加节点标签
            n1['labels'] = record.get('n1_labels', [])
            n2['labels'] = record.get('n2_labels', [])
            result.append({'n1': n1, 'rel': rel, 'n2': n2})
        return result

    # 根据实体名查询关系
    def findRelationByEntity(self, entity1):
        query = """
        MATCH (n1 {title: $entity1})-[rel]->(n2)
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity1=entity1)

    # 查询与 entity2 相关的关系
    def findRelationByEntity2(self, entity2):
        query = """
        MATCH (n1)-[rel]->(n2 {title: $entity2})
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity2=entity2)

    # 根据 entity1 和 relation 查找其他实体
    def findOtherEntities(self, entity, relation):
        query = """
        MATCH (n1 {title: $entity})-[rel {type: $relation}]->(n2)
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity=entity, relation=relation)

    # 根据 entity2 和 relation 查找上游实体
    def findOtherEntities2(self, entity, relation):
        query = """
        MATCH (n1)-[rel {type: $relation}]->(n2 {title: $entity})
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity=entity, relation=relation)

    # 查询两个实体之间的路径（保留原逻辑）
    def findRelationByEntities(self, entity1, entity2):
        query = """
        MATCH (n1 {title: $entity1})-[rel]->(n2 {title: $entity2})
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity1=entity1, entity2=entity2)

    # 检查是否存在特定实体-关系匹配
    def findEntityRelation(self, entity1, relation, entity2):
        query = """
        MATCH (n1 {title: $entity1})-[rel {type: $relation}]->(n2 {title: $entity2})
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query, entity1=entity1, relation=relation, entity2=entity2)

    # 查询数据库中所有关系
    def findAllRelation(self):
        query = """
        MATCH (n1)-[rel]->(n2)
        RETURN n1, rel, n2, labels(n1) AS n1_labels, labels(n2) AS n2_labels
        """
        return self._query_with_labels(query)

    # ================================
    # 完整递归反应路径查询（无深度限制）
    # ================================
    def findFullReactionPath(self, reactant_title):
        """
        从一个反应物出发，递归查找所有下游反应步骤及相关物质。
        包括：
          - 当前反应物参与的反应步骤；
          - 该步骤的所有反应物、产物、沸石；
          - 然后递归进入所有产物。
        """
        visited = set()
        results = []

        def traverse(reactant):
            if reactant in visited:
                return
            visited.add(reactant)

            # 查询该反应物参与的反应步骤
            query = """
            MATCH (r:ChemistryData {title: $reactant})-[:ChemistryReaction]->(step:ChemistryData)
            // 所有反应物（包括当前反应物）
            OPTIONAL MATCH (other_reactants:ChemistryData)-[:ChemistryReaction]->(step)
            // 所有产物
            OPTIONAL MATCH (step)-[:ChemistryReaction]->(p:ChemistryData)
            // 所有沸石
            OPTIONAL MATCH (zwelite:ZweliteData)-[:ChemistryReaction]->(step)
            RETURN DISTINCT r, step, other_reactants, p, zwelite,
                   labels(r) AS r_labels,
                   labels(step) AS step_labels,
                   labels(other_reactants) AS other_labels,
                   labels(p) AS p_labels,
                   labels(zwelite) AS zwelite_labels
            """
            records = self.graph.run(query, reactant=reactant)

            found_products = set()

            for record in records:
                step = record["step"]
                if not step:
                    continue

                # 当前反应物
                r = record["r"]
                if r:
                    r_dict = dict(r)
                    r_dict["labels"] = record["r_labels"]
                    results.append({"n1": r_dict, "rel": {}, "n2": dict(step)})

                # 该步骤的其他反应物
                other = record["other_reactants"]
                if other:
                    other_dict = dict(other)
                    other_dict["labels"] = record["other_labels"]
                    results.append({"n1": other_dict, "rel": {}, "n2": dict(step)})

                # 该步骤的沸石
                zw = record["zwelite"]
                if zw:
                    zw_dict = dict(zw)
                    zw_dict["labels"] = record["zwelite_labels"]
                    results.append({"n1": zw_dict, "rel": {}, "n2": dict(step)})

                # 该步骤的产物
                p = record["p"]
                if p:
                    p_dict = dict(p)
                    p_dict["labels"] = record["p_labels"]
                    results.append({"n1": dict(step), "rel": {}, "n2": p_dict})
                    found_products.add(p_dict["title"])

            # 递归进入所有产物
            for product in found_products:
                traverse(product)

        traverse(reactant_title)
        return results
