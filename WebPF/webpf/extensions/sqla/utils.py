#TODO: Move these to a separate utility package

from sqlalchemy import Table


def get_table_class_mappings(base):
    classes = (cls for cls in base._decl_class_registry.values() if hasattr(cls, '__table__'))
    mappings = dict((cls.__table__, cls) for cls in classes)
    return mappings


def classes_from_tables(base, tables, mappings=None):
    if mappings is None:
        mappings = get_table_class_mappings(base)
    return [mappings[table] for table in tables]


def get_join_hints_from_constraints(constraints, outer_operators=('is_', 'isnot')):
    hints = {}
    for constraint in constraints:
        try:
            operator_name = constraint.operator.__name__
            target = constraint.left
            target_table = constraint.left.table
            if operator_name in outer_operators:
                hints[target_table] = True
        except AttributeError:
            pass
    return hints


def get_related_classes(cls, base=None, mappings=None,):
    neighbors = []
    for rel in cls.__mapper__.relationships.values():
        if rel.secondary is None:
            neighbors.append(rel.mapper.class_)
        elif isinstance(rel.secondary, Table):
            if base is None:
               base = cls.__base__
            if mappings is None:
               mappings = get_table_class_mappings(base)
            neighbors.extend(classes_from_tables(base, [rel.secondary], mappings))
    return neighbors


def enumerate_paths(source, target, edges):
    queue = [(source, [source])]
    if source == target:
        yield []
        raise StopIteration

    while queue:
        node, path = queue.pop()
        neighbors = edges(node)
        possible = (neighbor for neighbor in neighbors if neighbor not in path)
        for neighbor in possible:
            new_path = path + [neighbor]
            if neighbor == target:
                yield new_path
            else:
                queue.append((neighbor, new_path))


def shortest_path(source, target, edges, default=[]):
    return list(next(enumerate_paths(source, target, edges), default))


def path_through(source, target, edges, include):
    if source == target:
         return []
    if not isinstance(include, (list, set)):
        include = [include]
    include = set(include)
    for path in enumerate_paths(source, target, edges):
        if include.intersect(path) == include:
            return path
    return None


def find_orm_joins(start, ends, get_edges=get_related_classes, join_hints={}):
    seen = set()
    join_path = []
    for target_node in ends:
        shortest = shortest_path(start, target_node, get_edges)
        new_nodes = (node for node in shortest if node not in seen)
        for path_node in new_nodes:
            seen.add(path_node)
            join_node = (path_node, join_hints.get(path_node, None))
            join_path.append(join_node)
    return join_path


#def get_tables_from_condition(condition):
#    tables = set()
#    if hasattr(condition, 'table'):
#        tables.add(condition.table)
#    if hasattr(condition, 'left'):
#        tables.update(get_tables_from_condition(condition.left))
#    if hasattr(condition, 'right'):
#        tables.update(get_tables_from_condition(condition.right))
#    if hasattr(condition, 'clauses'):
#        clause_tables = map(get_tables_from_condition, condition.clauses)
#        tables.update(reduce(set.union, clause_tables))
#    return tables


def get_tables_from_condition(condition):
    columns = get_columns_from_condition(condition)
    tables = set(column.table for column in columns)
    return tables


def get_columns_from_condition(condition):
    columns = set()
    if hasattr(condition, 'table'):
        columns.add(condition)
    if hasattr(condition, 'left'):
        columns.update(get_columns_from_condition(condition.left))
    if hasattr(condition, 'right'):
        columns.update(get_columns_from_condition(condition.right))
    if hasattr(condition, 'clauses'):
        clause_columns = map(get_columns_from_condition, condition.clauses)
        columns.update(reduce(set.union, clause_columns))
    return columns


def get_columns_with_usage_from_condition(condition):
    column_uses = set()
    if hasattr(condition, 'operator'):
        use = condition.operator
        if hasattr(condition, 'left'):
            if hasattr(condition.left, 'table'):
                column_uses.add((use, condition.left))
            else:
                column_uses.update(get_columns_with_usage_from_condition(condition.left))
        if hasattr(condition, 'right'):
            if hasattr(condition.right, 'table'):
                column_uses.add((use, condition.right))
            else:
                column_uses.update(get_columns_with_usage_from_condition(condition.right))
    else:
         if hasattr(condition, 'left'):
             column_uses.update(get_columns_with_usage_from_condition(condition.left))
         if hasattr(condition, 'right'):
             column_uses.update(get_columns_with_usage_from_condition(condition.right))
    if getattr(condition, 'supports_execution', False) and hasattr(condition, 'clauses'):
        use = condition.name
        for clause in condition.clauses:
            if hasattr(clause, 'table'):
                column_uses.add((use, clause))
            else:
                column_uses.update(get_columns_with_usage_from_condition(clause))
    else:
        if hasattr(condition, 'clauses'):
            for clause in condition.clauses:
                column_uses.update(get_columns_with_usage_from_condition(clause))
    return column_uses



def normalize_use(use):
    if hasattr(use, 'opstring'):
        return use.opstring
    elif hasattr(use, 'name'):
        return use.name
    else:
        return use


def suggest_query_parallelization(query, suggestions=[]):
    session = query.session
    # TODO: This should look at group by, etc. as well
    column_uses = get_columns_with_usage_from_condition(query.whereclause)
    column_uses = set((normalize_use(use), col) for use, col in column_uses)
    columns = set(col for use, col in column_uses)
    for possible_column, possible_parallelizations in suggestions:
        # Map InstrumentedAttribute to column
        possible_column = getattr(possible_column, '_query_clause_element', lambda:possible_column)()
        for usage, transformation_factory in possible_parallelizations:
            usage = normalize_use(usage)
            if usage is None:  # No use specified means all uses
                if possible_column in columns:
                    return transformation_factory(session)
            elif (usage, possible_column) in column_uses:
                return transformation_factory(session)
    return None
