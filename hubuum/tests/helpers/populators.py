"""Direct populator functions for testing purposes."""

from typing import Any, Dict, cast

from hubuum.exceptions import MissingParam
from hubuum.models.dynamic import HubuumClass, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.tools import get_model


class BasePopulator:
    """Base populator class. Direct access only. No API calls.

    Provides framework, no actual populating.
    """

    def _get_namespace(self, namespace: Namespace = None) -> Namespace:
        """Ensure we have a valid namespace.

        params: namespace: Namespace (default: self.namespace if available)
        """
        if namespace:
            return namespace
        else:
            if hasattr(self, "namespace") and self.namespace:
                return cast(Namespace, self.namespace)

        raise MissingParam("No namespace provided.")

    def create_in_model(self, model_name: str, **kwargs: Any) -> Any:
        """Create an instance in the given model.

        params: model_name: str
        params: kwargs: Any (key-value pairs, passed to model.objects.create)
        """
        model = get_model(model_name)
        if model:
            return model.objects.create(**kwargs)  # type: ignore
        else:
            raise MissingParam(f"Model {model_name} not found.")

    def create_class_direct(
        self, name: str = "Test", namespace: Namespace = None
    ) -> HubuumClass:
        """Create a dynamic class.

        params: name: str (default: "Test")
        params: namespace: Namespace (default: self.namespace if available)
        """
        namespace = self._get_namespace(namespace)

        attributes: Dict[str, Any] = {"name": name, "namespace": namespace}
        return HubuumClass.objects.create(**attributes)

    def create_object_direct(
        self,
        dynamic_class: HubuumClass = None,
        namespace: Namespace = None,
        json_data: Dict[str, Any] = None,
        **kwargs: Any,
    ) -> HubuumObject:
        """Create a dynamic object.

        params: dynamic_class: HubuumClass (default: None)
        params: namespace: Namespace (default: self.namespace if available)
        params: kwargs: Any
        """
        namespace = self._get_namespace(namespace)

        json_data = json_data or {"key": "value", "listkey": [1, 2, 3]}

        attributes: Dict[str, Any] = {
            "json_data": json_data,
            "namespace": namespace,
            **kwargs,
        }

        for key, value in kwargs.items():
            attributes[key] = value

        return HubuumObject.objects.create(dynamic_class=dynamic_class, **attributes)
