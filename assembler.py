import argparse
import json
import sys


OPS = {
    "LOADC": 7,
    "LC": 7,
    "PUSH": 7,

    "LOAD": 2,
    "READ": 2,
    "LD": 2,

    "STORE": 3,
    "WRITE": 3,
    "ST": 3,

    "SHL": 6,
    "SHIFTLEFT": 6,
}

LIMITS = {
    7: (0, (1 << 16) - 1),
    3: (0, (1 << 16) - 1),
    6: (0, (1 << 16) - 1),
    2: (0, (1 << 21) - 1),
}


def encode(a: int, b: int) -> bytes:
    word = (b << 3) | (a & 0b111)
    return bytes([word & 0xFF, (word >> 8) & 0xFF, (word >> 16) & 0xFF])


def normalize_op(op: str) -> str:
    return op.strip().upper().replace("-", "").replace("_", "")


def parse_program(text: str):
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Ожидается JSON-массив команд")

    program = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Команда #{i}: ожидается объект")

        if "op" not in item:
            raise ValueError(f"Команда #{i}: нет поля op")

        op_key = normalize_op(str(item["op"]))
        if op_key not in OPS:
            raise ValueError(f"Команда #{i}: неизвестная op={item['op']}")

        a = OPS[op_key]
        b = int(item.get("B", item.get("b", 0)))

        lo, hi = LIMITS[a]
        if not (lo <= b <= hi):
            raise ValueError(f"Команда #{i}: B={b} вне диапазона [{lo}..{hi}] для A={a}")

        program.append((a, b))
    return program


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="Путь к JSON файлу с программой")
    ap.add_argument("out", help="Путь к бинарному файлу-результату")
    ap.add_argument("--test", action="store_true", help="Печать A,B и байтов как в спецификации")
    args = ap.parse_args()

    with open(args.src, "r", encoding="utf-8") as f:
        program = parse_program(f.read())

    blob = bytearray()
    for a, b in program:
        blob.extend(encode(a, b))

    with open(args.out, "wb") as f:
        f.write(blob)

    if args.test:
        for a, b in program:
            bb = encode(a, b)
            print(f"A={a}, B={b}: 0x{bb[0]:02x}, 0x{bb[1]:02x}, 0x{bb[2]:02x}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
