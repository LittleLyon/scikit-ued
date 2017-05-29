# -*- coding: utf-8 -*-
from copy import copy
from collections.abc import Iterable
from functools import lru_cache
from itertools import product, takewhile, count
import numpy as np
from numpy import pi
from numpy.linalg import norm
from operator import mul
from scipy.special import k0 as bessel
import spglib
from warnings import warn

from . import AtomicStructure, Lattice, CIFParser, PDBParser, real_coords
from .. import (change_of_basis, transform, affine_map, change_basis_mesh, 
			    is_rotation_matrix, minimum_image_distance)

# Constants
m = 9.109*10**(-31)     #electron mass in kg
a0 = 0.5291             #in Angs
e = 14.4                #electron charge in Volt*Angstrom

def symmetry_expansion(items, *symmetry_operators):
    """
    Expands a a list of Transformable objects according to symmetry operators.
    
    Parameters
    ----------
    items : list of uediff.structure.Transformable objects 
        Typically AtomicStructures or Atoms
    symmetry_operators : tuple of ndarrays, shape (3,3)
        Symmetry operators
    
    Returns
    -------
    expanded : generator of uediff.structure.Transformable objects
    """
    for item in items:
        for sym_op in symmetry_operators:
            new_item = copy(item)
            new_item.transform(sym_op)
            yield new_item

class Crystal(AtomicStructure, Lattice):
	"""
	This object is the basis for inorganic crystals such as VO2, 
	and protein crystals such as bR. 
    
	Attributes
	----------
	symmetry_operators : list of ndarrays
		Symmetry operators that links the underlying AtomicStructure to the unit cell construction.
    
	unitcell : iterable of Atom objects
		List of atoms in the crystal unitcell. iter(Crystal) is a generator that yields
		the same atoms; this approach is preferred.
    
	atoms : iterable
		List of atoms in the asymmetric unit.
	"""

	def __init__(self, atoms, symmetry_operators = [np.eye(3)], **kwargs):
		kwargs.update({'items': atoms}) # atoms argument is an alias for AtomicStructure.items
		self.symmetry_operators = tuple(map(affine_map, symmetry_operators))
		super().__init__(**kwargs)
	
	def __iter__(self):
		yield from symmetry_expansion(self.atoms, *self.symmetry_operators)
	
	def __len__(self):
		return len(self.atoms)*len(self.symmetry_operators)
	
	def __repr__(self):
		return '< Crystal object with unit cell of {} atoms>'.format(len(self))

	@classmethod
	def from_cif(cls, path):
		"""
		Returns a Crystal object created from a CIF 1.0, 1.1 or 2.0 file.

		Parameters
		----------
		path : str
			File path
		
		References
		----------
		.. [#] Torbjorn Bjorkman, "CIF2Cell: Generating geometries for electronic structure programs", 
			   Computer Physics Communications 182, 1183-1186 (2011). doi: 10.1016/j.cpc.2011.01.013
		"""
		with CIFParser(filename = path) as parser:
			return Crystal(atoms = list(parser.atoms()), 
						   lattice_vectors = parser.lattice_vectors(), 
						   symmetry_operators = parser.symmetry_operators())

	@classmethod
	def from_pdb(cls, ID):
		"""
		Returns a Crystal object created from a Protein DataBank entry.

		Parameters
		----------
		ID : str
			Protein DataBank identification. The correct .pdb file will be downloaded,
			cached and parsed.
		"""
		parser = PDBParser(ID = ID)
		return Crystal(atoms = list(parser.atoms()), 
					   lattice_vectors = parser.lattice_vectors(),
					   symmetry_operators = parser.symmetry_operators())
	
	@property
	def unitcell(self):
		return list(iter(self))
	
	@property
	def spglib_cell(self):
		""" Returns the crystal structure in spglib's `cell` format."""
		lattice = np.array(self.lattice_vectors)
		positions = np.array([atom.frac_coords(self.lattice_vectors) for atom in iter(self)])
		numbers = np.array(tuple(atom.atomic_number for atom in iter(self)))
		return (lattice, positions, numbers)
	
	def periodicity(self):
		"""
		Crystal periodicity in x, y and z direction from the lattice constants.
		This is effectively a bounding cube for the unit cell, which is itself a unit cell.

		Parameters
		----------
		lattice : Lattice

		Returns
		-------
		out : tuple
			Periodicity in x, y and z directions [angstroms]
        
		Notes
		-----
		Warning: the periodicity of the lattice depends on its orientation in real-space.
		"""
		# By definition of a lattice, moving by the projection of all Lattice
		# vectors on an axis should return you to an equivalent lattice position
		e1, e2, e3 = np.eye(3)
		per_x = sum( (abs(np.vdot(e1,a)) for a in self.lattice_vectors) )
		per_y = sum( (abs(np.vdot(e2,a)) for a in self.lattice_vectors) )
		per_z = sum( (abs(np.vdot(e3,a)) for a in self.lattice_vectors) )
		return per_x, per_y, per_z
		
	def potential(self, x, y, z):
		"""
		Scattering potential calculated on a real-space mesh, assuming an
		infinite crystal.

		Parameters
		----------
		x, y, z : ndarrays
			Real space coordinates mesh. 
        
		Returns
		-------
		potential : `~numpy.ndarray`, dtype float
			Linear superposition of atomic potential [V*Angs]

		See also
		--------
		skued.minimum_image_distance
		"""
		# TODO: multicore
		potential = np.zeros_like(x, dtype = np.float)
		r = np.zeros_like(x, dtype = np.float)
		for atom in self:
			ax, ay, az = atom.coords
			r[:] = minimum_image_distance(x - ax, y - ay, z - az, 
										  lattice = self.lattice_vectors)
			potential += atom.potential(r)
		
		# Due to sampling, x,y, and z might pass through the center of atoms
		# Replace np.inf by the next largest value
		m = potential[np.isfinite(potential)].max()
		potential[np.isinf(potential)] = m
		return potential
	
	def scattering_vector(self, h, k, l):
		"""
		Returns the scattering vector G from Miller indices.
        
		Parameters
		----------
		h, k, l : int or ndarrays
			Miller indices.
        
		Returns
		-------
		G : array-like
			If `h`, `k`, `l` are integers, returns a single array of shape (3,)
			If `h`, `k`, `l` are arrays, returns three arrays Gx, Gy, Gz
		"""
		if isinstance(h, Iterable):
			return change_basis_mesh(h, k, l, basis1 = self.reciprocal_vectors, basis2 = np.eye(3))

		b1,b2,b3 = self.reciprocal_vectors
		return int(h)*b1 + int(k)*b2 + int(l)*b3
	
	def miller_indices(self, G):
		"""
		Returns the miller indices associated with a scattering vector.
        
		Parameters
		----------
		G : array-like, shape (3,)
			Scattering vector.
        
		Returns
		-------
		hkl : ndarray, shape (3,), dtype int
			Miller indices [h, k, l].
		"""
		G = np.asarray(G, dtype = np.float)
	
		# Transformation matric between reciprocal space and miller indices
		matrix_trans = np.empty(shape = (3,3), dtype = np.float)
		for i in range(len(self.reciprocal_vectors)):
			matrix_trans[:,i] = self.reciprocal_vectors[i]

		matrix_trans = np.linalg.inv(matrix_trans)
		return transform(matrix_trans, G).astype(np.int)
	
	def structure_factor_miller(self, h, k, l):
		"""
		Computation of the static structure factor from Miller indices.
        
		Parameters
		----------
		h, k, l : array_likes
			Miller indices. Can be given in a few different formats:
            
			``3 floats``
				returns structure factor computed for a single scattering vector
                
			``list of 3 coordinate ndarrays, shapes (L,M,N)``
				returns structure factor computed over all coordinate space
        
		Returns
		-------
		sf : ndarray, dtype complex
			Output is the same shape as h, k, or l.
        
		See also
		--------
		structure_factor
			Vectorized structure factor calculation for general scattering vectors.	
		"""
		return self.structure_factor(G = self.scattering_vector(h, k, l))
		
	def structure_factor(self, G):
		"""
		Computation of the static structure factor. This function is meant for 
		general scattering vectors, not Miller indices. 
        
		Parameters
		----------
		G : array-like
			Scattering vector. Can be given in a few different formats:
            
			``array-like of numericals, shape (3,)``
				returns structure factor computed for a single scattering vector
                
			``list of 3 coordinate ndarrays, shapes (L,M,N)``
				returns structure factor computed over all coordinate space
            
			WARNING: Scattering vector is not equivalent to the Miller indices.
        
		Returns
		-------
		sf : ndarray, dtype complex
			Output is the same shape as input G[0]. Takes into account
			the Debye-Waller effect.
        
		See also
		--------
		structure_factor_miller 
			For structure factors calculated from Miller indices.
		        
		Notes
		-----
		By convention, scattering vectors G are defined such that norm(G) = 4 pi s
		"""
		# Distribute input
		# This works whether G is a list of 3 numbers, a ndarray shape(3,) or 
		# a list of meshgrid arrays.
		Gx, Gy, Gz = G
		nG = np.sqrt(Gx**2 + Gy**2 + Gz**2)
		
		# Separating the structure factor into sine and cosine parts avoids adding
		# complex arrays together. About 3x speedup vs. using complex exponentials
		SFsin, SFcos = np.zeros(shape = nG.shape, dtype = np.float), np.zeros(shape = nG.shape, dtype = np.float)

		# Pre-allocation of form factors gives huge speedups
		dwf = np.empty_like(SFsin) 	# debye-waller factor
		atomff_dict = dict()
		for atom in self.atoms:
			if atom.element not in atomff_dict:
				atomff_dict[atom.element] = atom.electron_form_factor(nG)

		for atom in self: #TODO: implement in parallel?
			x, y, z = atom.coords
			arg = x*Gx + y*Gy + z*Gz
			atom.debye_waller_factor((Gx, Gy, Gz), out = dwf)
			atomff = atomff_dict[atom.element]
			SFsin += atomff * dwf * np.sin(arg)
			SFcos += atomff * dwf * np.cos(arg)
		
		return SFcos + 1j*SFsin
	
	def bounded_reflections(self, nG):
		"""
		Returns iterable of reflections (hkl) with norm(G) < nG
        
		Parameters
		----------
		nG : float
			Maximal scattering vector norm. By our convention, norm(G) = 4 pi s.
        
		Returns
		-------
		h, k, l : ndarrays, shapes (N,), dtype int
		"""
		if nG < 0:
			raise ValueError('Bound {} is negative.'.format(nG))
		
		# Determine the maximum index such that (i00) family is still within data limits
		#TODO: cache results based on max_index?
		bounded = lambda i : any([norm(self.scattering_vector(i,0,0)) <= nG, 
									norm(self.scattering_vector(0,i,0)) <= nG, 
									norm(self.scattering_vector(0,0,i)) <= nG])
		max_index = max(takewhile(bounded, count(0)))
		extent = range(-max_index, max_index + 1)
		h, k, l = np.split(np.array(list(product(extent, extent, extent)), dtype = np.int), 3, axis = -1)
		h, k, l = h.ravel(), k.ravel(), l.ravel()

		# we only have an upper bound on possible reflections
		# Let's filter down
		Gx, Gy, Gz = self.scattering_vector(h, k, l)
		norm_G = np.sqrt(Gx**2 + Gy**2 + Gz**2)
		in_bound = norm_G <= nG
		return h.compress(in_bound), k.compress(in_bound), l.compress(in_bound)
	
	def transform(self, *matrices):
		"""
		Transforms the real space coordinates according to a matrix.
        
		Parameters
		----------
		matrices : ndarrays, shape {(3,3), (4,4)}
			Transformation matrices.
		"""
		# Only rotation matrices should affect the symmetry operations
		for matrix in matrices:
			matrix = affine_map(matrix)  # Make sure it is 4x4
			if is_rotation_matrix(matrix):
				matrix[:3, 3] = 0  # remove translations
			self.symmetry_operators = tuple(transform(matrix, sym_op) for sym_op in self.symmetry_operators)
		
		super().transform(*matrices)