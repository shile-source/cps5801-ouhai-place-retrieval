"""Synthetic catalog validation; never opens actual model weights."""
import pytest
from src.retrieval.streamed_bge import validate_tensor_catalog, tensor_row_ranges


def test_all_names_and_shapes_required():
    validate_tensor_catalog({'synthetic.weight':(2,3)},{'synthetic.weight':[2,3]})


@pytest.mark.parametrize('actual',[{}, {'other':(2,3)}, {'synthetic.weight':(2,3),'extra':(1,)}])
def test_missing_or_extra_tensors_rejected(actual):
    with pytest.raises(ValueError,match='names differ'):
        validate_tensor_catalog({'synthetic.weight':(2,3)},actual)


def test_changed_shape_rejected():
    with pytest.raises(ValueError,match='shape mismatch'):
        validate_tensor_catalog({'synthetic.weight':(2,3)},{'synthetic.weight':(3,2)})


def test_large_embedding_reads_are_bounded_and_cover_every_row_once():
    shape=(250002,1024)
    ranges=tensor_row_ranges(shape,4)
    assert ranges[0][0]==0 and ranges[-1][1]==shape[0]
    assert all(a<b and (b-a)*shape[1]*4<=16*1024**2 for a,b in ranges)
    assert all(left[1]==right[0] for left,right in zip(ranges,ranges[1:]))


@pytest.mark.parametrize('shape,size',[((),4),((0,2),4),((2,5_000_000),4),((10,10),8)])
def test_unbounded_or_invalid_host_reads_are_rejected(shape,size):
    with pytest.raises(ValueError):tensor_row_ranges(shape,size)
