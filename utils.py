def num2text(number):
    if number == 0:
        return "Không đồng"

    units = ["", "nghìn", "triệu", "tỷ"]
    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_triplet(n, full=False):
        trăm = n // 100
        chục = (n % 100) // 10
        đơnvị = n % 10
        res = []

        if trăm > 0:
            res.append(digits[trăm] + " trăm")
        elif full:
            res.append("không trăm")

        if chục > 1:
            res.append(digits[chục] + " mươi")
            if đơnvị == 1:
                res.append("mốt")
            elif đơnvị == 5:
                res.append("lăm")
            elif đơnvị > 0:
                res.append(digits[đơnvị])
        elif chục == 1:
            res.append("mười")
            if đơnvị == 5:
                res.append("lăm")
            elif đơnvị > 0:
                res.append(digits[đơnvị])
        elif chục == 0 and đơnvị > 0:
            if full or trăm > 0:
                res.append("lẻ " + digits[đơnvị])
            else:
                res.append(digits[đơnvị])
        return " ".join(res)

    parts = []
    triplets = []
    while number > 0:
        triplets.append(number % 1000)
        number //= 1000

    for i in range(len(triplets) - 1, -1, -1):
        val = triplets[i]
        if val != 0:
            full = (i < len(triplets) - 1)  # Nếu không phải phần đầu
            part = read_triplet(val, full)
            if units[i]:
                part += " " + units[i]
            parts.append(part)

    return " ".join(parts).capitalize() + " đồng"