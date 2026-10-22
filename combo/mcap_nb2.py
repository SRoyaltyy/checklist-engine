import json, numpy as np, pandas as pd
END = pd.Timestamp("2024-12-31")
K = pd.read_parquet("keys_labels.parquet", columns=["ticker","date","split"]); key = K[["ticker","date"]].copy(); key["r"] = np.arange(len(K))
P = pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet", filters=[("date","<=",END)], columns=["ticker","date","close"])
P["ticker"] = P.ticker.astype(str); P["date"] = pd.to_datetime(P.date).astype("datetime64[ns]")
P = P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]); P["pc"] = P.groupby("ticker").close.shift(1)
X = key.merge(P[["ticker","date","pc"]], on=["ticker","date"], how="left").sort_values("r")
S = pd.read_parquet("nb_tags_v2/sec_shares_out_filed_le_2024.parquet"); S["filed"] = pd.to_datetime(S.filed); S = S[(S.filed <= END) & (S.val > 0)]
S = S.sort_values("filed").drop_duplicates(["ticker","filed"], keep="last")[["ticker","filed","val"]]
S["fd"] = (S.filed + pd.Timedelta(days=1)).astype("datetime64[ns]")  # strictly before D
X = pd.merge_asof(X.sort_values("date"), S.sort_values("fd")[["ticker","fd","val"]], left_on="date", right_on="fd", by="ticker", direction="backward").sort_values("r")
cap = X.val.values * X.pc.values
keep = ~(cap < 1e8); unk = np.isnan(cap)
np.save("mcap_keep.npy", keep); np.save("mcap_unknown.npy", unk)
for s in ["train","check"]:
    m = (K.split == s).values; print(s, "rows", m.sum(), "drop<100M", int((~keep & m).sum()), "cap unknown kept", int((unk & m).sum()))
TG = "nb_tags_v2"; ids = json.load(open(f"{TG}/nb_tags_ids.json"))["ids"]
NB = np.zeros((len(K), len(ids)), np.uint8); ANS = np.zeros(len(ids), np.int64)
for y in range(2020, 2025):
    d = pd.read_parquet(f"{TG}/nb_tags_{y}.parquet"); d["ticker"] = d.ticker.astype(str); d["date"] = pd.to_datetime(d.date).astype("datetime64[ns]")
    assert d.date.max() <= END and not d.duplicated(["ticker","date"]).any()
    d = d.merge(key, on=["ticker","date"])
    b = np.frombuffer(b"".join(d.packed.values), np.uint8).reshape(len(d), -1)
    A = np.stack([(b >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(len(d), -1)[:, :len(ids)]
    NB[d.r.values] = (A == 2); tr = (K.split.values[d.r.values] == "train"); ANS += (A[tr] > 0).sum(0)
np.save("nb2_bits.npy", NB); np.save("nb2_train_ans.npy", ANS); json.dump(ids, open("nb_ids.json", "w")); print("nb2", NB.shape)
