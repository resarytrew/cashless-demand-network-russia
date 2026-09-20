import numpy as np
from sbernet.robustness.alpha_sensitivity import dominant_retention, partition_similarity

def test_dominant_retention():
    ref=np.array([1,1,1,2,2])
    alt=np.array([5,5,6,7,7])
    out=dominant_retention(ref,alt,1)
    assert out["destination"]==5
    assert abs(out["retention"]-2/3)<1e-12

def test_partition_similarity_identity():
    x=np.array([0,0,1,1])
    out=partition_similarity(x,x)
    assert out["ari"]==1.0 and out["nmi"]==1.0
