def main():
# %%
    def fib(end: int) -> list:
        seq = [0, 1]
        while len(seq) < end + 1:
            seq.append(seq[-1] + seq[-2])
        return seq
    print(fib(40)[-1]) # Last element

# %%
if __name__ == "__main__":
    main()
