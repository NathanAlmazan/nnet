## NNET
A miniature implementation of Neural Network using numpy library only.

# How to use NNET?
You can train a neural network using NNET by importing the package and calling the base class to define your model architecture. 
The base class accepts an array of layers.

```python
  import nnet
  
  model = nnet.Sequential([
      nnet.layers.Dense((13, 10), nnet.activation.Tanh),
      nnet.layers.Dense((10, 8), nnet.activation.Tanh),
      nnet.layers.Dense((8, 2), nnet.activation.Sigmoid)
  ])
```

After defining your model architecture, you can train the model using 'fit' or 'fit_transform' methods. 'Fit' trains the data only while 'fit_transform' trains and produce prediction from input batches.

```python
  model.fit(X_train, Y_train, 500, nnet.loss.MeanSquaredError, nnet.optimizers.RMSProp(), X_val=X_test, Y_val=Y_test)
```

The following method accepts the following arguments.
| Argument        | Description                                                                                               |
| --------------- |:----------------------------------------------------------------------------------------------------------|
| X               | Input data. This should be in a numpy array with the dimensions of (sample_size, input_size)              |
| Y               | Labels. This should be in a numpy array with the dimensions of (sample_size, output_size)                 |
| epoch           | an integer number that refers to how many times you will train the model using the entire dataset         |
| loss_function   | your chosen loss function to compute the model error in predicting the actual values                      |
| optimizer       | your chosen optimizer algorithm to update the model's parameters                                          |
| X_val           | Validation input data. This should be in a numpy array with the dimensions of (sample_size, input_size)   |
| Y_val           | Validation Labels. This should be in a numpy array with the dimensions of (sample_size, output_size)      |
| accuracy_metric | lambda function for custom accuracy calculation                                                           |

Please notice that the optimizer has open and closed parenthesis compared to other imported modules. Because unlike other modules,
the optimizers are not abstract classes as each layer requires different instances of optimizers.

For examples of the framework's implementation, please check the test folder.

# How can I contribute?

You can contribute by cloning the repository and adding a pull request. Feel free to optimize the existing algorithms or add new methods. 
If you forked the repository, ensure your copy is always up-to-date. Please refer to this question for additional information on how to
ensure your forked repository is up-to-date. https://stackoverflow.com/questions/7244321/how-do-i-update-or-sync-a-forked-repository-on-github

In addition, please test your suggested improvements before submitting a pull request. If possible, please provide a screenshot or notebook of the test case.

>
> Thank you and Happy Coding!
>
