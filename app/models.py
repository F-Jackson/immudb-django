from django.db import models

from abc import ABC

from immudb_connection.connection import starting_db


immu_client = starting_db(user='immudb', password='immudb')
print(immu_client)

class ImmudbModel(models.Model):
    nome = models.CharField(max_length=155)
    # def save(self, *args, **kwargs):
    #     values = {}
    #     for field in self.__class__._meta.fields:
    #         value = getattr(self, field.name)
    #         values[field.name] = str(value)

    #     if self.expireableDateTime:
    #         self.immu_client.expireableSet(
    #             self.pk.encode(),
    #             json.dumps(values).encode(),
    #             datetime.now() + timedelta(**self.expireableDateTime)
    #         )
    #     else:
    #         self.immu_client.set(
    #             self.pk.encode(),
    #             json.dumps(values).encode()
    #         )
    #     super().save(*args, **kwargs)

    # def delete(self):
    #     deleteRequest = DeleteKeysRequest(keys=[self.pk.encode()])
    #     self.immu_client.delete(deleteRequest)

    def get_obj(self, pk=str):
        return immu_client.get(pk.encode())
