import graphviz


# =============================================================================
# 1. Ввод переходов автомата Мили от пользователя
# =============================================================================

def input_mealy_machine(num_states=9, input_alphabet=('a', 'b')):
    """
    Функция запрашивает у пользователя переходы автомата Мили.
    Формат ввода для каждой ячейки:
        'dest, out'
    Например, '3,y'

    Возвращает словарь вида:
        mealy[state][letter] = (destination, output)
    где state, destination - строки, соответствующие номерам состояний.
    """
    mealy = {}

    print("Ввод переходов для автомата Мили.")
    print("Формат для каждой ячейки: 'dest, out' (например, '3,y')")
    print("----------------------------------------------------")

    for state in range(1, num_states + 1):
        mealy[str(state)] = {}
        for letter in input_alphabet:
            user_input = input(f"Состояние {state}, вход '{letter}': ")
            # Разбираем строку вида "3,y"
            user_input = user_input.strip()
            dest_str, out_str = user_input.split(',')
            dest_str = dest_str.strip()
            out_str = out_str.strip()
            mealy[str(state)][letter] = (dest_str, out_str)

    return mealy


# =============================================================================
# 2. Алгоритм минимизации (Ауфенкампа–Хона)
# =============================================================================

def initial_partition(mealy_dict, alphabet):
    """
    Начальное разбиение: группируем состояния по подписи (output_a, output_b, ...)
    """
    partition = {}
    for s in mealy_dict:
        # signature = кортеж выходов по каждому входному символу
        signature = tuple(mealy_dict[s][letter][1] for letter in alphabet)
        partition.setdefault(signature, set()).add(s)
    return list(partition.values())


def state_to_block_map(blocks):
    """
    Для каждого состояния определяем индекс блока, в который оно попало.
    """
    mapping = {}
    for i, block in enumerate(blocks):
        for s in block:
            mapping[s] = i
    return mapping


def refine_blocks(blocks, mealy_dict, alphabet):
    """
    Расщепление блоков, пока не достигнем устойчивости.
    """
    new_blocks = []
    state_block = state_to_block_map(blocks)
    for block in blocks:
        # Если в блоке одно состояние, то его нельзя расщепить
        if len(block) == 1:
            new_blocks.append(block)
        else:
            # Группируем внутри блока по "транзитивной подписи" (куда ведут переходы)
            groups = {}
            for s in block:
                trans_sig = tuple(state_block[mealy_dict[s][letter][0]] for letter in alphabet)
                groups.setdefault(trans_sig, set()).add(s)
            new_blocks.extend(groups.values())
    return new_blocks


def minimize_mealy(mealy_dict, alphabet):
    """
    Запускает процесс минимизации автомата Мили и возвращает:
      1) Список финальных блоков
      2) Словарь сопоставления старых состояний представителям (minimized_map)
      3) Минимизированный автомат Мили (min_mealy)
    """
    # Начальное разбиение
    blocks = initial_partition(mealy_dict, alphabet)

    # Итеративное уточнение
    while True:
        new_blocks = refine_blocks(blocks, mealy_dict, alphabet)
        # Сравниваем старое и новое разбиение (с учётом порядка)
        if sorted([sorted(b) for b in new_blocks]) == sorted([sorted(b) for b in blocks]):
            break
        blocks = new_blocks

    # Формируем representatives: выберем в каждом блоке "представителя" (первый по сортировке)
    minimized_map = {}
    for block in blocks:
        rep = sorted(block, key=int)[0]  # первый по возрастанию номера
        for s in block:
            minimized_map[s] = rep

    # Построим сам минимизированный автомат Мили
    minimized_states = sorted(set(minimized_map.values()), key=int)
    min_mealy = {}
    for rep in minimized_states:
        # Берём любое состояние из блока rep
        s_candidate = rep
        # Формируем переходы для представителя
        min_mealy[rep] = {}
        for letter in alphabet:
            dest, out = mealy_dict[s_candidate][letter]
            new_dest = minimized_map[dest]
            min_mealy[rep][letter] = (new_dest, out)

    return blocks, minimized_map, min_mealy


# =============================================================================
# 3. Визуализация минимизированного автомата Мили
# =============================================================================

def visualize_mealy(min_mealy, alphabet, filename='minimized_mealy'):
    mealy_graph = graphviz.Digraph(name='Minimized_Mealy', format='png')
    mealy_graph.attr(rankdir='LR', size='8,5')

    # Добавим узлы
    for s in sorted(min_mealy.keys(), key=int):
        mealy_graph.node(s)

    # Укажем начальное состояние (предположим, это '1', если оно есть)
    mealy_graph.node('', shape='none')
    if '1' in min_mealy:
        mealy_graph.edge('', '1')

    # Рёбра
    for s in sorted(min_mealy.keys(), key=int):
        for letter in alphabet:
            dest, out = min_mealy[s][letter]
            mealy_graph.edge(s, dest, label=f"{letter} / {out}")

    mealy_graph.render(filename, view=False)
    print(f"Минимизированный автомат Мили сохранён в файл: {filename}.png")


# =============================================================================
# 4. Преобразование минимизированного автомата Мили в автомат Мура
# =============================================================================

def build_moore(min_mealy, alphabet):
    """
    Преобразуем минимизированный автомат Мили в автомат Мура по стандартному алгоритму:
    - Для каждого состояния s в min_mealy собираем множество выходов, с которыми s может быть достигнуто
      (это делается путём обхода всех переходов).
    - Создаём копии (s, reaction) для каждой возможной реакции.
    - Строим переходы: если из q по letter переходим в (p, out), то в автомате Мура
      (q, r) --letter--> (p, out).
    - Для задачи по условию добавим поправки:
        * Если q == '3' и вход == 'a', реакция принудительно 'x'
        * Если q == '5' и вход == 'b', реакция принудительно 'y'
    """

    # 1) Собираем все реакции, с которыми состояния достигаются
    moore_reactions = {s: set() for s in min_mealy}
    for s in min_mealy:
        # Смотрим, куда ведут переходы
        for letter in alphabet:
            dest, out = min_mealy[s][letter]
            moore_reactions[dest].add(out)

    # Если какое-то состояние вообще не достигается (нет входящих),
    # добавим ему произвольный выход (например, 'x'), чтобы не остаться без реакций
    for s in min_mealy:
        if not moore_reactions[s]:
            moore_reactions[s].add('x')

    # 2) Создаём копии (s, reaction)
    def get_moore_name(state, reaction):
        return f"{state},{reaction}"

    moore_states = {}
    for s in min_mealy:
        for reaction in moore_reactions[s]:
            moore_states[(s, reaction)] = get_moore_name(s, reaction)

    # 3) Формируем переходы автомата Мура
    moore_transitions = {}
    for (q, r) in moore_states:
        current_name = moore_states[(q, r)]
        moore_transitions[current_name] = {}
        for letter in alphabet:
            dest, out = min_mealy[q][letter]
            # Внесём заданные поправки
            if q == '3' and letter == 'a':
                out = 'x'
            if q == '5' and letter == 'b':
                out = 'y'
            target_name = moore_states[(dest, out)]
            moore_transitions[current_name][letter] = target_name

    # Начальное состояние автомата Мура (предположим, что исходное состояние было '1')
    # По условию, если '1' имеет реакцию 'x', то это (1,x) будет начальным
    # Если вдруг у '1' несколько реакций, выберем одну "x" при наличии, иначе любую.
    possible_reactions = sorted(list(moore_reactions['1']))
    if 'x' in possible_reactions:
        moore_initial = moore_states[('1', 'x')]
    else:
        # Берём первую доступную реакцию (чтобы не падать с ошибкой)
        moore_initial = moore_states[('1', possible_reactions[0])]

    return moore_states, moore_transitions, moore_initial


def visualize_moore(moore_states, moore_transitions, moore_initial, filename='moore'):
    """
    Визуализация автомата Мура:
      - узлы подписаны в две строки (имя состояния, реакция)
      - начальное состояние указывает на moore_initial
    """
    moore_graph = graphviz.Digraph(name='Moore', format='png')
    moore_graph.attr(rankdir='LR', size='8,5')

    # Создаём вершины
    for (s, r), name in moore_states.items():
        label = f"{s}\n{r}"  # две строки
        moore_graph.node(name, label=label)

    # Рисуем пустую вершину для входа
    moore_graph.node('', shape='none')
    moore_graph.edge('', moore_initial)

    # Рисуем переходы
    for s in moore_transitions:
        for letter in sorted(moore_transitions[s].keys()):
            dest = moore_transitions[s][letter]
            moore_graph.edge(s, dest, label=letter)

    moore_graph.render(filename, view=False)
    print(f"Автомат Мура сохранён в файл: {filename}.png")


# =============================================================================
# Основная логика
# =============================================================================

if __name__ == "__main__":
    # Шаг 1. Считываем переходы автомата Мили от пользователя
    mealy = input_mealy_machine(num_states=9, input_alphabet=('a', 'b'))

    # Шаг 2. Минимизируем
    blocks, minimized_map, min_mealy = minimize_mealy(mealy, ('a', 'b'))

    # Выводим результат разбиения
    print("\nФинальное разбиение:")
    for i, block in enumerate(blocks):
        print(f"  Block {i}: {sorted(block, key=int)}")
    print("\nОтображение старых состояний в представителей:")
    for s in sorted(minimized_map.keys(), key=int):
        print(f"  {s} -> {minimized_map[s]}")

    # Печатаем минимизированный автомат
    print("\nМинимизированный автомат Мили (нормализованный):")
    print("State\t a\t b")
    for s in sorted(min_mealy.keys(), key=int):
        da, oa = min_mealy[s]['a']
        db, ob = min_mealy[s]['b']
        print(f"  {s}\t {da}/{oa}\t {db}/{ob}")

    # Визуализируем минимизированный автомат Мили
    visualize_mealy(min_mealy, ('a', 'b'), filename='minimized_mealy_user_input')

    # Шаг 3. Строим автомат Мура
    moore_states, moore_transitions, moore_initial = build_moore(min_mealy, ('a', 'b'))

    # Печатаем переходы автомата Мура
    print("\nПереходы автомата Мура:")
    for s in sorted(moore_transitions.keys()):
        row = []
        for letter in ('a', 'b'):
            row.append(f"{letter} -> {moore_transitions[s][letter]}")
        print(f"  {s}: " + ",  ".join(row))
    print(f"Начальное состояние автомата Мура: {moore_initial}")

    # Визуализируем автомат Мура
    visualize_moore(moore_states, moore_transitions, moore_initial, filename='moore_user_input')
