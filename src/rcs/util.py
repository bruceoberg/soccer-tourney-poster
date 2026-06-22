#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes

from typing import Annotated, Literal, get_args, get_origin, overload

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

# container BaseModel for injecting a field into a containee BaseModel at model_validate() time.
# meant for containee classes intended to be serialized as a dict mapping their name to each object.
# the name Field() should be marked exclude=True. this prevents the name from being serialized twice.

class CMpStrInjected:  # tag = mpsi
	"""Dict type that injects each dict key into child model under a specified field name."""

	@overload
	def __class_getitem__[T: BaseModel](cls, params: tuple[type[T], type[Literal[str]]]) -> type[dict[str, T]]: ...

	def __class_getitem__(cls, params: tuple) -> type:
		clsInner, clsKey = params
		assert issubclass(clsInner, BaseModel), f"CMpStrInject: {clsInner} must be a BaseModel subclass"
		assert get_origin(clsKey) is Literal, f"CMpStrInject: {clsKey} must be a Literal[str]"
		(strKeyField,) = get_args(clsKey)
		
		def ObjValidate(obj: dict) -> dict:
			objResult = {}
			for strKey, objVal in obj.items():
				if isinstance(objVal, clsInner):
					# Already constructed — just verify key consistency
					assert getattr(objVal, strKeyField) == strKey, (
						f"CMpStrInject: key {strKey!r} doesn't match "
						f"{strKeyField}={getattr(objVal, strKeyField)!r}"
					)
					objResult[strKey] = objVal
				else:
					assert isinstance(objVal, dict)
					objResult[strKey] = clsInner.model_validate({strKeyField: strKey} | objVal)
			return objResult

		class _Validator:
			@classmethod
			def __get_pydantic_core_schema__(
				cls,
				source_type: type,
				handler: GetCoreSchemaHandler,
			) -> core_schema.CoreSchema:
				return core_schema.no_info_plain_validator_function(ObjValidate)

		return Annotated[dict[str, clsInner], _Validator]