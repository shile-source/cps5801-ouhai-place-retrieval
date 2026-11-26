"""Synthetic catalog validation; never opens actual model weights."""
import pytest
from src.retrieval.streamed_bge import validate_tensor_catalog


def test_all_names_and_shapes_required():
    validate_tensor_catalog({'synthetic.weight':(2,3)},{'synthetic.weight':[2,3]})


@pytest.mark.parametrize('actual',[{}, {'other':(2,3)}, {'synthetic.weight':(2,3),'extra':(1,)}])
def test_missing_or_extra_tensors_rejected(actual):
    with pytest.raises(ValueError,match='names differ'):
        validate_tensor_catalog({'synthetic.weight':(2,3)},actual)


def test_changed_shape_rejected():
    with pytest.raises(ValueError,match='shape mismatch'):
        validate_tensor_catalog({'synthetic.weight':(2,3)},{'synthetic.weight':(3,2)})
