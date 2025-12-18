import argparse
import json
import sys
from array import array
from pathlib import Path

def decode_program(raw):
    if len(raw) % 3 != 0:
        raise ValueError("Длина двоичного файла должна быть кратна 3 байтам")
    out = []
    for i in range(0, len(raw), 3):
        value = int.from_bytes(raw[i:i+3], byteorder="little", signed=False)
        a = value & 0b111
        b = value >> 3
        out.append((a, b))
    return out

def ensure_mem(mem, addr, hard_cap=2_500_000):
    if addr < 0:
        raise ValueError("Отрицательный адрес памяти")
    if addr >= hard_cap:
        raise ValueError(f"Слишком большой адрес памяти: {addr}")
    if addr >= len(mem):
        mem.extend([0] * (addr + 1 - len(mem)))

def load_init(mem, init_path):
    if init_path is None:
        return
    obj = json.loads(Path(init_path).read_text(encoding="utf-8"))
    if isinstance(obj, dict) and "start" in obj and "values" in obj:
        start = int(obj["start"])
        vals = obj["values"]
        if not isinstance(vals, list):
            raise ValueError("init.json: поле values должно быть массивом")
        for i, v in enumerate(vals):
            addr = start + i
            ensure_mem(mem, addr)
            mem[addr] = int(v) & 0xFFFFFFFF
        return
    if isinstance(obj, dict) and "values" in obj and isinstance(obj["values"], dict):
        for k, v in obj["values"].items():
            addr = int(k)
            ensure_mem(mem, addr)
            mem[addr] = int(v) & 0xFFFFFFFF
        return
    raise ValueError("init.json: ожидаю {start, values:[...]} или {values:{addr:value,...}}")

def parse_range(s):
    if s is None:
        return 0, 256
    if ":" not in s:
        raise ValueError("Диапазон должен быть в формате start:end")
    a, b = s.split(":", 1)
    start = int(a)
    end = int(b)
    if start < 0 or end < start:
        raise ValueError("Неверный диапазон")
    return start, end

def run(program, mem):
    stack = []
    pc = 0
    while pc < len(program):
        a, b = program[pc]
        if a == 7:
            stack.append(b & 0xFFFFFFFF)
        elif a == 2:
            ensure_mem(mem, b)
            stack.append(int(mem[b]) & 0xFFFFFFFF)
        elif a == 3:
            if len(stack) < 2:
                raise RuntimeError("STORE: в стеке нужно минимум 2 значения (value, base_addr)")
            base = int(stack.pop()) & 0xFFFFFFFF
            value = int(stack.pop()) & 0xFFFFFFFF
            addr = (base + b) & 0xFFFFFFFF
            ensure_mem(mem, addr)
            mem[addr] = value
        elif a == 6:
            if len(stack) < 1:
                raise RuntimeError("SHL: стек пуст")
            x = int(stack.pop()) & 0xFFFFFFFF
            addr = (x + b) & 0xFFFFFFFF
            ensure_mem(mem, addr)
            shift = int(mem[addr]) & 0x1F
            stack.append(((x << shift) & 0xFFFFFFFF))
        else:
            raise RuntimeError(f"Неизвестная команда A={a} на позиции {pc}")
        pc += 1
    return stack

def dump_memory(mem, start, end, out_path, stack=None):
    ensure_mem(mem, max(0, end-1)) if end > 0 else None
    values = [int(mem[i]) for i in range(start, end)]
    obj = {
        "range": {"start": start, "end": end},
        "values": values
    }
    if stack is not None:
        obj["stack"] = [int(x) for x in stack]
    Path(out_path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(prog="interpreter.py")
    ap.add_argument("program", help="Путь к двоичному файлу программы (3 байта на команду)")
    ap.add_argument("dump", help="Путь к JSON-файлу дампа памяти")
    ap.add_argument("--range", dest="mem_range", default=None, help="Диапазон памяти start:end для дампа (например 0:256)")
    ap.add_argument("--init", default=None, help="JSON с начальными данными памяти")
    ap.add_argument("--mem", type=int, default=4096, help="Начальный размер памяти (элементов)")
    args = ap.parse_args()

    try:
        raw = Path(args.program).read_bytes()
        program = decode_program(raw)
        mem = array("I", [0]) * int(args.mem)
        load_init(mem, args.init)
        stack = run(program, mem)
        start, end = parse_range(args.mem_range)
        dump_memory(mem, start, end, args.dump, stack=stack)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
