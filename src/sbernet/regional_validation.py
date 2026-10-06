"""Leakage-safe regional generalisation diagnostics for frozen profile labels."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kruskal
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def assert_group_separation(groups: np.ndarray, train: np.ndarray, test: np.ndarray) -> None:
    """Raise instead of silently accepting a geographic group in both folds."""
    if set(groups[train]).intersection(groups[test]):
        raise AssertionError("Region leakage across grouped cross-validation fold")


def grouped_prediction(frame: pd.DataFrame, features: list[str], folds: int, seed: int) -> pd.DataFrame:
    data = frame.loc[frame.profile.isin(list("ABCDEFG")), ["profile", "region", *features]].dropna(subset=["region"]).copy()
    y, groups = data.pop("profile").to_numpy(), data.pop("region").astype(str).to_numpy(); x = data.to_numpy()
    cv = GroupKFold(n_splits=min(folds, len(np.unique(groups))))
    models = {
        "multinomial_logistic": Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=seed))]),
        "random_forest": Pipeline([("impute", SimpleImputer(strategy="median")), ("model", RandomForestClassifier(n_estimators=400, min_samples_leaf=3, class_weight="balanced", random_state=seed, n_jobs=-1))]),
    }
    rows=[]
    for name, model in models.items():
        actual=[]; predicted=[]; probabilities=[]; classes=None
        for train, test in cv.split(x, y, groups):
            assert_group_separation(groups, train, test); model.fit(x[train],y[train]); actual.extend(y[test]); predicted.extend(model.predict(x[test])); probabilities.append(model.predict_proba(x[test])); classes=model.classes_
        rows.append({"model":name,"n":len(y),"folds":cv.get_n_splits(),"groups":len(np.unique(groups)),"macro_f1":f1_score(actual,predicted,average="macro"),"balanced_accuracy":balanced_accuracy_score(actual,predicted),"accuracy":accuracy_score(actual,predicted),"log_loss":log_loss(actual,np.vstack(probabilities),labels=classes),"features":";".join(features),"split":"GroupKFold_region"})
    return pd.DataFrame(rows)


def region_only_baseline(frame: pd.DataFrame, folds: int) -> pd.DataFrame:
    data=frame.loc[frame.profile.isin(list("ABCDEFG")),["profile","region"]].dropna().copy(); y=data.profile.to_numpy(); groups=data.region.astype(str).to_numpy(); cv=GroupKFold(n_splits=min(folds,len(np.unique(groups))))
    actual=[]; predicted=[]
    for train,test in cv.split(data,y,groups):
        assert_group_separation(groups,train,test)
        # Held-out regions have no observed profile: use the training majority.
        label=pd.Series(y[train]).value_counts().sort_index().idxmax(); actual.extend(y[test]); predicted.extend([label]*len(test))
    return pd.DataFrame([{"model":"region_only_unseen_region_majority","n":len(y),"folds":cv.get_n_splits(),"macro_f1":f1_score(actual,predicted,average="macro",zero_division=0),"balanced_accuracy":balanced_accuracy_score(actual,predicted),"accuracy":accuracy_score(actual,predicted),"definition":"training-majority for entirely unseen regional groups"}])


def within_region_residuals(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    result=frame.copy()
    for value in variables:
        median=result.groupby("region",dropna=False)[value].transform("median")
        result[f"{value}_within_region"] = result[value] - median
    return result


def within_region_tests(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    rows=[]
    for variable in variables:
        data=frame[["profile",variable]].dropna(); groups=[item[variable].to_numpy() for _,item in data.groupby("profile",sort=True)]
        h,p=kruskal(*groups); n,k=len(data),len(groups); eps=max(0.,(h-k+1)/(n-k))
        rows.append({"variable":variable,"n":n,"groups":k,"kruskal_h":h,"p_value":p,"epsilon_squared":eps})
    return pd.DataFrame(rows)
