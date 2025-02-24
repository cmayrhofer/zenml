---
description: How to configure MLOps tooling and infrastructure with stacks
---

In ZenML, a **Stack** represents a set of configurations for your MLOps tools
and infrastructure. For instance, you might want to:

- Orchestrate your ML workflows with [Kubeflow](../../mlops-stacks/orchestrators/kubeflow.md),
- Save ML artifacts in an [Amazon S3](../../mlops-stacks/artifact-stores/amazon-s3.md) bucket,
- Track ML metadata in a managed [MySQL](../../mlops-stacks/metadata-stores/mysql.md) database,
- Track your experiments with [Weights & Biases](../../mlops-stacks/experiment-trackers/wandb.md),
- Deploy models on Kubernetes with [Seldon](../../mlops-stacks/model-deployers/seldon.md) or [KServe](../../mlops-stacks/model-deployers/kserve.md),

Any such combination of tools and infrastructure can be registered as a 
separate stack in ZenML. Since ZenML code is tooling-independent, you can 
switch between stacks with a single command and then automatically execute your
ML workflows on the desired stack without having to modify your code.

## Stack Components

In ZenML, each MLOps tool is associated to a specific **Stack Component**,
which is responsible for one specific task of your ML workflow. 

For instance, each ZenML stack includes an *Orchestrator* which is responsible
for the execution of the steps within your pipeline, an *Artifact Store* which
is responsible for storing the artifacts generated by your pipelines, and a
*Metadata Store* that tracks what artifact was produced or consumed by which
pipeline steps.

{% hint style="info" %}
Check out the [Categories of MLOps Tools](../../mlops-stacks/categories.md)
page for a detailed overview of available stack components in ZenML.
{% endhint %}

##  Orchestrator, Artifact Store, and Metadata Store

As mentioned above, orchestrators, artifact stores, and metadata stores are the
three components that need to be in every ZenML stack. The interaction of these
three components enables a lot of the magic of ZenML, such as data and model
versioning, automated artifact lineage tracking, automated caching, and more.

![Orchestrators, Artifact Store, and Metadata Store](../../assets/localstack.png)

### Orchestrator

The [Orchestrator](../../mlops-stacks/orchestrators/orchestrators.md) is the 
component that defines how and where each pipeline step is executed when
calling `pipeline.run()`. By [default](../../mlops-stacks/orchestrators/local.md),
all runs are executed locally, but by configuring a different orchestrator you
can, e.g., automatically execute your ML workflows on 
[Kubeflow](../../mlops-stacks/orchestrators/kubeflow.md) instead.

### Artifact Stores

Under the hood, all the artifacts in our ML pipeline are automatically stored
in an [Artifact Store](../../mlops-stacks/artifact-stores/artifact-stores.md).
By [default](../../mlops-stacks/artifact-stores/local.md), this is simply a
place in your local file system, but we could also configure ZenML to store
this data in a cloud bucket like [Amazon S3](../../mlops-stacks/artifact-stores/amazon-s3.md) 
or any other place instead.

### Metadata Stores

In addition to the artifact itself, ZenML automatically stores metadata about
each pipeline run in a [Metadata Store](../../mlops-stacks/metadata-stores/metadata-stores.md). 
By default, this uses an [SQLite](../../mlops-stacks/metadata-stores/sqlite.md)
database on your local machine, but we could again switch it out for another
storage type, such as a [MySQL](../../mlops-stacks/metadata-stores/mysql.md)
database deployed in the cloud.

## Stack Component Flavors

The specific tool you are using is called a **Flavor** of the stack component. 
E.g., *Kubeflow* is a flavor of the *Orchestrator* stack component.

Out-of-the-box, ZenML already comes with a wide variety of flavors, which are
either built-in or enabled through the installation of specific
[Integrations](../../mlops-stacks/integrations.md).

## The default Stack

By default, ZenML itself and every [Repository](#repositories) that you create
already come with an initial active `default` stack, which features:
- A [local orchestrator](../../mlops-stacks/orchestrators/local.md),
- A [local artifact store](../../mlops-stacks/artifact-stores/local.md),
- A [local SQLite metadata store](../../mlops-stacks/metadata-stores/sqlite.md).

If you followed the code examples in the 
[Steps and Pipelines](../steps-pipelines/steps-and-pipelines.md) section, then you have already
used this stack implicitly to run all of your pipelines.

## Listing Stacks, Stack Components, and Flavors

You can see a list of all your *registered* stacks with the following command:

```shell
zenml stack list
```

Similarly, you can see all *registered* stack components of a specific type using:

```shell
zenml <STACK_COMPONENT> list
```

In order to see all the *available* flavors for a specific stack component, use:

```shell
zenml <STACK_COMPONENT> flavor list
```

{% hint style="info" %}
Our CLI features a wide variety of commands that let you manage and use your stacks.
If you would like to learn more, please run: "`zenml stack --help`"
or visit [our CLI docs](https://apidocs.zenml.io/latest/cli/).
{% endhint %}

## Registering New Stacks

You can combine various MLOps tools into a ZenML stack as follows:

1. [Register a stack component](#registering-stack-components) for each tool 
using `zenml <STACK_COMPONENT> register`,
2. [Register a stack](#registering-a-stack) to bring all tools together using
`zenml stack register`,
3. [Activate the stack](#activating-a-stack) using `zenml stack set`. Now all
your code is automatically executed using the desired tools / infrastructure.

### Registering Stack Components

First, you need to create a new instance of the respective stack component
with the desired flavor using `zenml <STACK_COMPONENT> register <NAME> --flavor=<FLAVOR>`. 
Most flavors require further parameters that you can pass as additional
arguments `--param=value`, similar to how we passed the flavor.

E.g., to register a *local* artifact store, we could use the following command:

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=local \
    --path=/path/to/your/store
```

In case you do not know all the available parameters, you can also use the 
interactive mode to register stack components. This will then walk you through 
each parameter (to skip just press ENTER):

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=local -i
```


Afterwards, you should be able to see the new artifact store in the
list of registered artifact stores, which you can access using the following command:

```shell
zenml artifact-store list
```

{% hint style="info" %}
Our CLI features a wide variety of commands that let you manage and use your
stack components and flavors. If you would like to learn more, please run
`zenml <STACK_COMPONENT> --help` or visit [our CLI docs](https://apidocs.zenml.io/latest/cli/).
{% endhint %}

### Registering a Stack

After registering each tool as the respective stack component, you can combine
all of them into one stack using the `zenml stack register` command:

```shell
zenml stack register <STACK_NAME> \
    --orchestrator <ORCHESTRATOR_NAME> \
    --artifact-store <ARTIFACT_STORE_NAME> \
    --metadata-store <METADATA_STORE_NAME> \
    ...
```

{% hint style="info" %}
You can use `zenml stack register --help` to see a list of all possible 
arguments to the `zenml stack register` command, including a list of which 
option to use for which stack component.
{% endhint %}

### Activating a Stack

Finally, to start using the stack you just registered, set it as active:

```shell
zenml stack set <STACK_NAME>
```
Now all your code is automatically executed using this stack.

{% hint style="info" %}
Some advanced stack component flavors might require connecting to remote 
infrastructure components prior to running code on the stack. This can be done
using `zenml stack up`. See the [Managing Stack States](../advanced-usage/stack-state-management.md)
section for more details.
{% endhint %}

## Changing Stacks

If you have multiple stacks configured, you can switch between them using the
`zenml stack set` command, similar to how you [activate a stack](#activating-a-stack).

## Unregistering Stacks

To unregister (delete) a stack and all of its components, run

```shell
zenml stack delete <STACK_NAME>
```

to delete the stack itself, followed by

```shell
zenml <STACK_COMPONENT> delete <STACK_COMPONENT_NAME>
```

to delete each of the individual stack components.

{% hint style="warning" %}
If you provisioned infrastructure related to the stack, make sure to
deprovision it using `zenml stack down --force` before unregistering the stack.
See the [Managing Stack States](../advanced-usage/stack-state-management.md) section for more details.
{% endhint %}
